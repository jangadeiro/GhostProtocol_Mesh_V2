# -*- coding: utf-8 -*-
"""
GhostProtocol Virtual Machine (GVM)
TR: Akıllı kontratları izole bir ortamda çalıştıran sanal makine.
EN: Virtual machine that runs smart contracts in an isolated environment.
"""
import json

class GhostVM:
    def __init__(self):
        # TR: İzin verilen güvenli fonksiyonlar (Sandbox)
        # EN: Allowed safe functions (Sandbox)
        self.safe_builtins = {
            'abs': abs, 'dict': dict, 'int': int, 'list': list, 
            'len': len, 'str': str, 'sum': sum, 'range': range,
            'max': max, 'min': min, 'round': round, 'bool': bool,
            'float': float, 'set': set, 'tuple': tuple
        }

    def validate_code(self, code_str):
        # TR: Kodda yasaklı ifadeleri kontrol et (import, open, exec vb.)
        # EN: Check for banned keywords in code (import, open, exec etc.)
        banned = ['import', 'open', 'exec', 'eval', '__import__', 'os.', 'sys.', 'subprocess', 'input']
        for b in banned:
            if b in code_str:
                return False, f"Security Violation: '{b}' is forbidden."
        return True, "OK"

    def execute_contract(self, code, method_name, args, current_state):
        """
        TR: Kontrat kodunu çalıştırır ve yeni durumu döndürür.
        EN: Executes contract code and returns the new state.
        """
        # 1. Güvenlik Kontrolü / Security Check
        valid, msg = self.validate_code(code)
        if not valid: return {'success': False, 'error': msg}

        # 2. Ortam Hazırlığı / Environment Setup
        # TR: Durumu kopyalayarak veriyoruz ki doğrudan referansla bozulmasın
        # EN: We pass a copy of the state so it doesn't get corrupted by reference
        local_scope = {'state': current_state.copy() if current_state else {}}
        
        try:
            # TR: Kodu kısıtlı ortamda derle ve çalıştır
            # EN: Compile and run code in restricted environment
            exec(code, {"__builtins__": self.safe_builtins}, local_scope)
            
            # TR: İstenen metodu çağır
            # EN: Call the requested method
            if method_name in local_scope and callable(local_scope[method_name]):
                # Fonksiyonu çalıştır / Run function
                result = local_scope[method_name](*args)
                
                # TR: Yeni durumu al
                # EN: Get new state
                new_state = local_scope.get('state', current_state)
                
                return {'success': True, 'result': result, 'new_state': new_state}
            else:
                return {'success': False, 'error': f"Method '{method_name}' not found."}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

# TR: Örnek bir Akıllı Kontrat Şablonu
# EN: Example Smart Contract Template
EXAMPLE_CONTRACT = """
# GhostProtocol Smart Contract
# State is automatically injected as a dictionary named 'state'

def init():
    state['counter'] = 0
    state['owner'] = 'GhostNetwork'
    return "Initialized"

def increment(amount):
    current = state.get('counter', 0)
    state['counter'] = current + int(amount)
    return state['counter']

def get_counter():
    return state.get('counter', 0)
"""