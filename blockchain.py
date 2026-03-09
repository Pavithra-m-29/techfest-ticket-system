import hashlib, json, time

class Blockchain:
    def __init__(self):
        self.chain = []
        self.create_block("Genesis Block")

    def create_block(self, data):
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time.time(),
            "data": data,
            "previous_hash": self.chain[-1]["hash"] if self.chain else "0"
        }
        block["hash"] = self.hash(block)
        self.chain.append(block)
        return block

    def hash(self, block):
        return hashlib.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()

blockchain = Blockchain()