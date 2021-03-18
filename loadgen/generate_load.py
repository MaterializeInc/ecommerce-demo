import barnum, random, time, json
from mysql.connector import connect, Error
from kafka import KafkaProducer

# CONFIG
userSeedCount      = 10000
itemSeedCount      = 1000
purchaseGenCount   = 100000
purchaseGenEveryMS = 100
pageviewMultiplier = 75
itemInventoryMin   = 1000
itemInventoryMax   = 5000
itemPriceMin       = 5
itemPriceMax       = 500
kafkaHost          = 'kafka:9092'
kafkaTopic         = 'pageviews'
channels           = ['organic search', 'paid search', 'referral', 'social', 'display']

# INSERT TEMPLATES
item_insert     = "INSERT INTO shop.items (name, price, inventory) VALUES ( %s, %s, %s )"
user_insert     = "INSERT INTO shop.users (email, is_vip) VALUES ( %s, %s )"
purchase_insert = "INSERT INTO shop.purchases (user_id, item_id, quantity, purchase_price) VALUES ( %s, %s, %s, %s )"

#Initialize Kafka
producer = KafkaProducer(bootstrap_servers=[kafkaHost],
                         value_serializer=lambda x: 
                         json.dumps(x).encode('utf-8'))

def generatePageview(user_id, product_id):
    return {
        "user_id": user_id,
        "url": f'/products/{product_id}',
        "channel": random.choice(channels),
        "received_at": int(time.time())
    }

try:
    with connect(
        host="mysql",
        user='root',
        password='debezium',
    ) as connection:
        with connection.cursor() as cursor:
            print("Initializing shop database...")
            cursor.execute('DROP DATABASE IF EXISTS shop;')
            cursor.execute('CREATE DATABASE shop;')
            cursor.execute(
                """CREATE TABLE  shop.users
                    (
                        id SERIAL PRIMARY KEY,
                        email VARCHAR(255),
                        is_vip BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                );"""
            )
            cursor.execute(
                """CREATE TABLE shop.items
                    (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(100),
                        price DECIMAL(7,2),
                        inventory INT,
                        inventory_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                );"""
            )
            cursor.execute(
                """CREATE TABLE shop.purchases
                    (
                        id SERIAL PRIMARY KEY,
                        user_id BIGINT UNSIGNED REFERENCES user(id),
                        item_id BIGINT UNSIGNED REFERENCES item(id),
                        status TINYINT UNSIGNED DEFAULT 1,
                        quantity INT UNSIGNED DEFAULT 1,
                        purchase_price DECIMAL(12,2),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                );"""
            )
            connection.commit()
            print("Seeding data...")
            cursor.executemany(
                item_insert,
                [
                    (
                        barnum.create_nouns(),
                        random.randint(itemPriceMin*100,itemPriceMax*100)/100,
                        random.randint(itemInventoryMin,itemInventoryMax)
                    ) for i in range(itemSeedCount)
                ]
            )
            cursor.executemany(
                user_insert,
                [
                    (
                        barnum.create_email(),
                        (random.randint(0,10) > 8)
                     ) for i in range(userSeedCount)
                ]
            )
            connection.commit()

            print("Getting item ID and PRICEs...")
            cursor.execute("SELECT id, price FROM shop.items")
            item_prices = [(row[0], row[1]) for row in cursor]

            print("Preparing to loop + seed kafka pageviews and purchases")
            for i in range(purchaseGenCount):
                # Get a user and item to purchase
                purchase_item = random.choice(item_prices)
                purchase_user = random.randint(0,userSeedCount-1)
                purchase_quantity = random.randint(1,5)

                # Write purchaser pageview
                producer.send(kafkaTopic, key=b'test', value=generatePageview(purchase_user, purchase_item[0]))

                # Write random pageviews
                for i in range(pageviewMultiplier):
                    producer.send(kafkaTopic, key=b'test', value=generatePageview(random.randint(0,userSeedCount), random.randint(0,itemSeedCount)))

                # Write purchase row
                cursor.execute(
                    purchase_insert,
                    (
                        purchase_user,
                        purchase_item[0],
                        purchase_quantity,
                        purchase_item[1] * purchase_quantity
                    )
                )
                connection.commit()

                #Pause
                time.sleep(purchaseGenEveryMS/1000)


    connection.close()

except Error as e:
    print(e)