import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MockRedis:
    def __init__(self):
        self.store = {}
        self.is_down = False

    def get(self, key):
        if self.is_down:
            raise ConnectionError("Redis connection failed")
        return self.store.get(key)

    def set(self, key, value, ex=None):
        if self.is_down:
            raise ConnectionError("Redis connection failed")
        self.store[key] = value

    def delete(self, key):
        if self.is_down:
            raise ConnectionError("Redis connection failed")
        if key in self.store:
            del self.store[key]

class ProductService:
    def __init__(self, redis_client):
        self.db = {
            1: {"productId": 1, "name": "Laptop Gaming", "price": 1500.0, "version": 1}
        }
        self.redis = redis_client
        self.cache_ttl = 600

    def get_product_by_id(self, product_id):
        cache_key = f"product:{product_id}"
        try:
            cached_data = self.redis.get(cache_key)
            if cached_data:
                logging.info(f"Cache hit cho product_id={product_id}")
                return cached_data
        except Exception as e:
            logging.warning(f"Loi Redis doc cache: {e}. Fallback xuong DB.")

        if product_id not in self.db:
            raise ValueError("San pham khong ton tai")

        product = self.db[product_id]
        try:
            self.redis.set(cache_key, product, ex=self.cache_ttl)
        except Exception as e:
            logging.warning(f"Loi Redis ghi cache: {e}")

        return product

    def update_product(self, product_id, name, price):
        if product_id not in self.db:
            raise ValueError("San pham khong ton tai trong DB")

        self.db[product_id]["name"] = name
        self.db[product_id]["price"] = price
        self.db[product_id]["version"] += 1

        cache_key = f"product:{product_id}"
        try:
            self.redis.delete(cache_key)
            logging.info(f"CacheEvict thanh cong cho product_id={product_id}")
        except Exception as e:
            logging.error(f"Loi Redis khi xoa cache (@CacheEvict): {e}. Thuc hien co che backup TTL.")

        return self.db[product_id]

if __name__ == "__main__":
    redis_mock = MockRedis()
    service = ProductService(redis_mock)

    logging.info("--- 1. Doc san pham lan dau (Cache Miss) ---")
    print(service.get_product_by_id(1))

    logging.info("--- 2. Doc san pham lan hai (Cache Hit) ---")
    print(service.get_product_by_id(1))

    logging.info("--- 3. Cap nhat san pham (Su dung @CacheEvict) ---")
    updated = service.update_product(1, "Laptop Gaming Pro", 1700.0)
    print("Updated DB:", updated)

    logging.info("--- 4. Doc lai san pham sau khi cap nhat (Cache Miss va tu nap lai DB) ---")
    print(service.get_product_by_id(1))
