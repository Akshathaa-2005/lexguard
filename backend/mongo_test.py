from pymongo import MongoClient
import certifi

uri = "mongodb+srv://USERNAME:PASSWORD@cluster0.6x2zcv9.mongodb.net/?retryWrites=true&w=majority"

client = MongoClient(
    uri,
    tls=True,
    tlsAllowInvalidCertificates=False,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=10000
)

print(client.admin.command("ping"))