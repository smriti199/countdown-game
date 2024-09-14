from flask import Flask, render_template, request, jsonify, g
import random
import itertools
import enchant
import sqlite3
import os

app = Flask(__name__)

# Database setup
DATABASE = 'countdown_game.db'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()

# Create tables if they don't exist
if not os.path.exists(DATABASE):
    init_db()

# Constants for Numbers Game
BIG_NUMBERS = [25, 50, 75, 100]
LITTLE_NUMBERS = list(range(1, 11)) * 2
TARGET_RANGE = (100, 999)
TIME_LIMIT = 30
ROUNDS = 3

# Constants for Letters Game
VOWELS = 'AEIOU'
CONSONANTS = 'BCDFGHJKLMNPQRSTVWXYZ'

# Create an English dictionary
dictionary = enchant.Dict("en_US")


# Numbers Game functions (from previous implementation)
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


# Letters Game functions
def is_valid_word(word, available_letters):
    if not dictionary.check(word):
        return False
    word_chars = list(word.upper())
    for char in word_chars:
        if char not in available_letters:
            return False
        available_letters.remove(char)
    return True

def find_possible_words(letters):
    possible_words = []
    for i in range(3, len(letters) + 1):
        for combo in itertools.combinations(letters, i):
            word = ''.join(combo)
            if dictionary.check(word):
                possible_words.append(word)
    return sorted(possible_words, key=len, reverse=True)[:10]  # Return top 10 longest words


def select_letter(letter_type):
    if letter_type == 'vowel':
        return random.choice(VOWELS)
    else:
        return random.choice(CONSONANTS)
    
def update_high_scores(game_type, score):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO high_scores (game_type, score) VALUES (?, ?)", (game_type, score))
    db.commit()

def get_high_scores(game_type):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT score FROM high_scores WHERE game_type = ? ORDER BY score DESC LIMIT 5", (game_type,))
    return [row[0] for row in cursor.fetchall()]


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/numbers')
def numbers_game():
    high_scores = get_high_scores('numbers')
    return render_template('numbers.html', high_scores=high_scores)

@app.route('/letters')
def letters_game():
    high_scores = get_high_scores('letters')
    return render_template('letters.html', high_scores=high_scores)

@app.route('/start_numbers_game', methods=['POST'])
def start_numbers_game():
    big_count = int(request.form['big_count'])
    numbers = select_numbers(big_count)
    target = generate_target()
    return jsonify({'numbers': numbers, 'target': target})

@app.route('/submit_numbers_solution', methods=['POST'])
def submit_numbers_solution():
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
    update_high_scores('numbers', score)
    high_scores = get_high_scores('numbers')
    
    return jsonify({
        'message': message,
        'score': score,
        'optimal_solution': optimal_solution,
        'high_scores': high_scores
    })

@app.route('/select_letter', methods=['POST'])
def select_letter_route():
    letter_type = request.form['letter_type']
    letter = select_letter(letter_type)
    return jsonify({'letter': letter})

@app.route('/submit_letters_solution', methods=['POST'])
def submit_letters_solution():
    data = request.json
    letters = data['letters']
    user_word = data['word'].upper()
    
    if is_valid_word(user_word, letters.copy()):
        score = len(user_word)
        message = f'Valid word! You scored {score} points.'
    else:
        score = 0
        message = 'Invalid word. No points awarded.'
    
    possible_words = find_possible_words(letters)
    update_high_scores('letters', score)
    high_scores = get_high_scores('letters')
    
    return jsonify({
        'message': message,
        'score': score,
        'possible_words': possible_words,
        'high_scores': high_scores
    })

if __name__ == '__main__':
    app.run(debug=True)