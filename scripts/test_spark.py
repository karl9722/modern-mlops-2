from pyspark.sql import SparkSession

spark = (
    SparkSession.builder
    .master("local[2]")
    .appName("modern-mlops-test")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("ERROR")

data = [
    (1, 250000),
    (2, 320000),
    (3, 410000),
]

df = spark.createDataFrame(data, ["house_id", "price"])

df.show()

print("Nombre de maisons :", df.count())
print("Spark fonctionne correctement !")

spark.stop()
