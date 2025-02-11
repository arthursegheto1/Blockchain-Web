import hashlib
import json
import requests
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from flask_cors import CORS  

class Blockchain:

    def __init__(self):
        self.current_transactions = []
        self.chain = []
        self.nodes = set()

        self.new_block(previous_hash='1', proof=100) # Cria o bloco gênese (primeiro bloco da blockchain)

    def new_block(self, proof, previous_hash=None):
        """
        Cria um novo bloco na blockchain
        """
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        self.current_transactions = [] # Reseta a lista de transações atuais

        self.chain.append(block)
        
        self.broadcast_block(block) # Transmite o novo bloco para todos os nós

        self.resolve_conflicts() # Resolve conflitos automaticamente após criar um novo bloco

        return block

    def new_transaction(self, sender, recipient, amount):
        """
        Cria uma nova transação para ser incluída no próximo bloco minerado
        """
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount,
        })

        self.broadcast_transaction(sender, recipient, amount) # Transmite a nova transação para todos os nós

        return self.last_block['index'] + 1

    @staticmethod
    def hash(block):
        """
        Cria um hash SHA-256 de um bloco
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        """
        Retorna o último bloco da blockchain
        """
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """
        Algoritmo simples de Prova de Trabalho (Proof of Work)
        """
        proof = 0
        while not self.valid_proof(last_proof, proof):
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Valida a Prova de Trabalho
        """
        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def valid_chain(self, chain):
        """
        Verifica se uma blockchain fornecida é válida
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            if block['previous_hash'] != self.hash(last_block): # Verifica se o hash do bloco anterior está correto
                return False

            if not self.valid_proof(last_block['proof'], block['proof']): # Verifica se a Prova de Trabalho está correta
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        """
        Algoritmo de consenso para resolver conflitos
        """
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)

        for node in neighbours:
            url = f"{node}/chain"
            try:
                print(f"Buscando cadeia do nó: {url}")
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    length = response.json().get('length')
                    chain = response.json().get('chain')

                    if length and chain and length > max_length and self.valid_chain(chain):
                        max_length = length
                        new_chain = chain
            except (requests.exceptions.RequestException, KeyError) as e:
                print(f"Falha ao buscar ou processar cadeia do nó {node}: {e}")
                continue

        if new_chain:
            self.chain = new_chain
            print("Cadeia substituída por uma mais longa e válida")
            return True

        print("Nenhum conflito encontrado ou a cadeia já é a mais longa")
        return False

    def broadcast_transaction(self, sender, recipient, amount):
        """
        Transmite uma nova transação para todos os nós da rede
        """
        for node in self.nodes:
            url = f"{node}/transactions/new"
            try:
                requests.post(url, json={
                    'sender': sender,
                    'recipient': recipient,
                    'amount': amount,
                }, timeout=5)
            except requests.exceptions.RequestException as e:
                print(f"Falha ao transmitir transação para o nó {node}: {e}")

    def broadcast_block(self, block):
        """
        Transmite um novo bloco para todos os nós da rede
        """
        for node in self.nodes:
            url = f"{node}/blocks/new"
            try:
                requests.post(url, json=block, timeout=5)
            except requests.exceptions.RequestException as e:
                print(f"Falha ao transmitir bloco para o nó {node}: {e}")

app = Flask(__name__) # Instancia um nó
CORS(app)  # Habilita CORS para todas as rotas

node_identifier = str(uuid4()).replace('-', '') # Gera um identificador único para este nó

blockchain = Blockchain() # Instancia a Blockchain

@app.route('/mine', methods=['GET'])
def mine_block():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': 'Bloco minerado com sucesso!',
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        'previous_hash': block['previous_hash'],
    }

    return jsonify(response), 200

@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    data = request.get_json()

    required_fields = ["sender", "recipient", "amount"]
    if not all(field in data for field in required_fields):
        return "Dados inválidos", 400

    index = blockchain.new_transaction(data["sender"], data["recipient"], data["amount"])

    response = {
        'message': f'Transação adicionada ao bloco {index}!',
        'total_transacoes': len(blockchain.current_transactions)
    }

    return jsonify(response), 201

@app.route('/chain', methods=['GET'])
def full_chain():
    """
    Rota para obter toda a blockchain
    """
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200

@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    """
    Rota para registrar novos nós na rede
    """
    values = request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return "Erro: Forneça uma lista válida de nós", 400

    for node in nodes:
        normalized_node = node.strip().rstrip('/')
        if not normalized_node.startswith('http://') and not normalized_node.startswith('https://'):
            normalized_node = f'http://{normalized_node}'
        blockchain.nodes.add(normalized_node)

    response = {
        'message': 'Novos nós foram adicionados',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201

@app.route('/blocks/new', methods=['POST'])
def new_block():
    """
    Rota para adicionar um novo bloco à blockchain
    """
    values = request.get_json()
    required = ['index', 'timestamp', 'transactions', 'proof', 'previous_hash']

    if not all(k in values for k in required):
        return 'Valores ausentes', 400

    block = {
        'index': values['index'],
        'timestamp': values['timestamp'],
        'transactions': values['transactions'],
        'proof': values['proof'],
        'previous_hash': values['previous_hash'],
    }

    blockchain.chain.append(block) # Adiciona o bloco à cadeia

    blockchain.resolve_conflicts() # Resolve conflitos após receber um novo bloco

    response = {'message': 'Bloco adicionado à cadeia'}
    return jsonify(response), 201

if __name__ == '__main__':
   from argparse import ArgumentParser

   parser = ArgumentParser()
   parser.add_argument('-p', '--port', default=5000, type=int, help='porta para escutar')
   args = parser.parse_args()
   port = args.port

   app.run(host='0.0.0.0', port=port)
