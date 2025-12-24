# GhostProtocol Developer Handbook

**GhostProtocol Developer Handbook: Smart Contracts** **Version:** 1.0 (GhostVM v1)  
**Vision:** Uncensorable, Decentralized, Free Internet.

---

## 1. Introduction and Architecture

GhostProtocol utilizes an isolated Python virtual machine called **GhostVM** (Ghost Virtual Machine). This structure allows developers to write immutable applications running on the blockchain using familiar Python syntax.

### Core Principles
* **Isolation (Sandbox):** Contracts cannot access main server files, network sockets, or the operating system. They can only operate on their allocated state (memory).
* **Determinism:** A contract code must always produce the exact same output given the same input and starting state. Therefore, variables like random (randomness) or system time are restricted or must be provided via deterministic methods.
* **Persistence:** Contract data (State) is stored forever in GhostProtocol's distributed database (SQLite + Blockchain).

---

## 2. Contract Anatomy and Lifecycle

Every smart contract file is written in `.py` format (or as text) and must possess the following skeleton:

### Mandatory Components
1.  **`state` Variable (Global):**
    * Automatically injected into the contract by GhostVM.
    * **Type:** `dict` (Dictionary).
    * **Function:** It is the place where data is persistently stored.
2.  **`init()` Method:**
    * **When does it run?** It runs only once when the contract is first uploaded to the network (Deploy).
    * **Function:** Assigns initial values to variables (e.g., Token name, Owner address).

### Example Skeleton
```python
# The 'state' memory of the contract is defined automatically.
def init():
    # Setup settings
    state['owner'] = 'CreatorAddress'
    state['is_active'] = True
    return "Contract Initialized"

def my_custom_function(arg1, arg2):
    # Business logic
    if state['is_active']:
        return "Active"
    return "Inactive"
```

### 3. API Reference: Allowed Methods (Whitelist)
GhostVM restricts Python's standard library to ensure security. The following list contains ALL built-in functions and descriptions available for use in your contracts.

## Data Type Converters
Arguments coming from the network are in String format by default; you must convert them before processing.

**int(x):** Converts text or decimal numbers to an integer (e.g., int("50") -> 50).

**float(x):** Converts text or integers to a decimal number (e.g., float("3.14") -> 3.14).

**str(x):** Converts a number or object to text (e.g., str(100) -> "100").

**bool(x):** Returns whether a value is True or False (e.g., bool(1) -> True).

## Data Structures

**dict():** Creates a dictionary holding Key-Value pairs. Similar to JSON.

**list():** Creates an ordered data list.

**set():** Creates a set consisting of unique (non-repeating) elements.

**tuple():** Creates an immutable ordered list.

### 4. Mathematical and Logical Tools

**len(x):** Returns the length of a list or text.

**sum(x):** Sums the numbers in a list.

**max(x):** Finds the largest value in a list.

**min(x):** Finds the smallest value in a list.

**abs(x):** Returns the absolute (positive) value of a number.

**round(x):** Rounds a decimal number to the nearest integer.

**range(x):** Generates a range of numbers for loops.

### Banned Commands (Unusable!)
The following commands are blocked for security reasons. If used, the contract will not load or run:

**import** (Calling external libraries)

**open** (File reading/writing)

**exec, eval** (Dynamic code execution)

**os, sys, subprocess** (System commands)

**print** (Runs only on the server console for debug, does not output to the network)

### 5. State Management
The most critical part of smart contracts is state management; this is the brain of the contract.

**Reading Data (get):** Using the `.get()` method when reading data prevents errors if a datum does not exist.

**Bad Method:** `balance = state['user_1'] (May error)`.

**Good Method:** `balance = state.get('user_1', 0) (Returns default value)`.

**Writing Data (set):** Assignment is done using the key directly.

**Example:** `state['total_supply'] = 1000000.`

### Contract Creation and Interaction Guide
To implement a contract, the GhostProtocol Dashboard or CLI (Command Line) is used.

**Step 1:** Coding: Write your code in a text editor. Pay attention to indentation (4 spaces).

**Step 2:** Deploy:

**Action:** "Deploy New Contract".

**Input:** Your written Python code.

**Fee:** 2.0 GHOST (To prevent network spam).

**Output:** You are given a unique Contract Address (e.g., CNT7a9b2...). Save this address!

**Step 3:** Call / Interact:

**Action:** "Call Contract".

Input 1 (Address): CNT7a9b2....

Input 2 (Method): The name of the function you want to call (e.g., transfer).

Input 3 (Arguments): Function parameters. Separate with commas if multiple (e.g., mehmet, 50).

Fee: 0.001 GHOST (Per transaction).

### 6. Best Practices and Security
Critical tips for developers:

**Input Validation:** Never trust data coming from outside. Check argument types and limits. Always convert using int() or float(). Return error messages for invalid inputs.

**Avoid Infinite Loops:** Do not write loops like while True:. You will hit GhostVM's execution time limit, your transaction will be cancelled, but your fee will be burned.

**Memory Saving:** Do not save unnecessary large data (large texts, images) to the state dictionary. This increases transaction costs. Only store necessary data (balances, IDs, statuses).

**Error Messages:** Return understandable messages with return at the end of your functions. This ensures the user understands the result of the transaction (success or failure).

### 7. Example: Simple "Notepad" Contract

``` Python

def init():
    # Initialize dictionary to hold notes
    state['notes'] = {}
    return "Notepad Ready"

def add_note(title, content):
    # Overwrites if title exists
    state['notes'][str(title)] = str(content)
    return f"Note added: {title}"

def read_note(title):
    # Get note, warn if missing
    return state['notes'].get(str(title), "No such note.")

def delete_note(title):
    if title in state['notes']:
        del state['notes'][title]
        return "Note deleted."
    return "Note not found."
```

Built for the GhostProtocol Ecosystem.
