import os
import json
from confluent_kafka import Producer, Consumer

# ⚠️ Make sure your .env file or Render environment has these set:
# KAFKA_BOOTSTRAP_SERVERS, KAFKA_CA, KAFKA_CERT, KAFKA_KEY

def verify_aiven_connection():
    print("🚀 Testing Aiven Kafka Connection...")
    
    # 1. Setup certificates
    ca_content = os.getenv("KAFKA_CA")
    if not ca_content:
        print("❌ FAILED: KAFKA_CA environment variable not found.")
        return
        
    print("✅ Creating SSL certificates from environment variables...")
    with open("ca.pem", "w") as f:
        f.write(ca_content.replace("\\n", "\n"))
    with open("service.cert", "w") as f:
        f.write(os.getenv("KAFKA_CERT", "").replace("\\n", "\n"))
    with open("service.key", "w") as f:
        f.write(os.getenv("KAFKA_KEY", "").replace("\\n", "\n"))

    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS")
    if not bootstrap_servers or "9092" in bootstrap_servers:
        print(f"⚠️ WARNING: Your bootstrap server looks wrong: {bootstrap_servers}")
        print("Aiven ports are usually NOT 9092. Double check your Aiven connection settings!")
        
    conf = {
        'bootstrap.servers': bootstrap_servers,
        'security.protocol': 'SSL',
        'ssl.ca.location': 'ca.pem',
        'ssl.certificate.location': 'service.cert',
        'ssl.key.location': 'service.key',
        'client.id': 'debug-test-client',
        'socket.timeout.ms': 5000,
        'message.timeout.ms': 5000,
    }

    # 2. Test Producer
    try:
        print(f"📡 Connecting to Bootstrap Servers: {bootstrap_servers}")
        producer = Producer(conf)
        print("✅ Producer successfully instantiated (Credentials accepted)")
        print("🎉 Your Render -> Aiven connection is fully working!")
        
    except Exception as e:
        print(f"❌ Connection Failed: {str(e)}")
        if "SSL" in str(e):
            print("👉 Hint: This is a certificate issue. Make sure you copied the WHOLE cert including -----BEGIN... and -----END...")
        elif "timeout" in str(e).lower():
            print("👉 Hint: This is a networking issue. Make sure your bootstrap server host and PORT are exactly what Aiven provided.")

if __name__ == "__main__":
    verify_aiven_connection()
