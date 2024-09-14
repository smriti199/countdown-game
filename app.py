# app.py
from flask import Flask, render_template, request, jsonify
import random
import itertools

app = Flask(__name__)

# Constants
BIG_NUMBERS = [25, 50, 75, 100]
LITTLE_NUMBERS = list(range(1, 11)) * 2
TARGET_RANGE = (100, 999)
TIME_LIMIT = 30
ROUNDS = 3

def select_numbers(big_count):
    big = random.sample(BIG_NUMBERS, big_count)
    little = random.sample(LITTLE_NUMBERS, 6 - big_count)
    return big + little

def generate_target():
    return random.randint(*TARGET_RANGE)

def evaluate_expression(expression, numbers):
    try:
        used_numbers = [int(n) for n in expression.replace('+',',').replace('-',',').replace('*',',').replace('/',',').split(',') if n.strip()]
        if not all(used_numbers.count(n) <= numbers.count(n) for n in set(used_numbers)):
            return None
        return eval(expression)
    except:
        return None

def find_solution(numbers, target):
    for i in range(1, len(numbers) + 1):
        for combo in itertools.combinations(numbers, i):
            for perm in itertools.permutations(combo):
                for ops in itertools.product(['+', '-', '*', '/'], repeat=i-1):
                    expr = ''.join(f'{n}{op}' for n, op in zip(perm, ops + ('',)))
                    if evaluate_expression(expr, numbers) == target:
                        return expr
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
def start_game():
    big_count = int(request.form['big_count'])
    numbers = select_numbers(big_count)
    target = generate_target()
    return jsonify({'numbers': numbers, 'target': target})

@app.route('/submit_solution', methods=['POST'])
def submit_solution():
    data = request.json
    numbers = data['numbers']
    target = data['target']
    user_solution = data['solution']
    
    result = evaluate_expression(user_solution, numbers)
    if result is None:
        return jsonify({'message': 'Invalid solution', 'score': 0, 'optimal_solution': find_solution(numbers, target)})
    
    difference = abs(result - target)
    if difference == 0:
        score = 10
        message = 'Congratulations! You found the exact solution.'
    elif difference <= 5:
        score = 7
        message = f'Close! Your solution evaluates to {result}. You were off by {difference}.'
    elif difference <= 10:
        score = 5
        message = f'Not bad. Your solution evaluates to {result}. You were off by {difference}.'
    else:
        score = 0
        message = f'Try again. Your solution evaluates to {result}. You were off by {difference}.'
    
    optimal_solution = find_solution(numbers, target)
    return jsonify({'message': message, 'score': score, 'optimal_solution': optimal_solution})

if __name__ == '__main__':
    app.run(debug=True)