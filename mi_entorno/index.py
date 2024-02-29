from flask import Flask, render_template, request
pila= []
from lark import Lark
import re
from tabla_predictiva import tabla_predictiva


app = Flask(__name__)

mensajeERROR = ""
texto = ""
bandera2 = False

@app.route('/')
def pagina():
    return render_template('formulario.html', bandera='')

class Token:
    def __init__(self, tipo, valor):
        self.tipo = tipo
        self.valor = valor

    def __repr__(self):
        return f"Token({self.tipo}, {self.valor})"

TOKEN_TYPES = {
    'DELETE': r'\bdelete\b', 'FROM': r'\bfrom\b', 'LETTER': r'[a-zA-Z]', 'WHERE': r'\bwhere\b', 
    'COM': r"'", 'PESO': r'\$', 'IGUAL': r'\=', 'NUMBER': r'\d', 'COM': r"'",
    'WHITESPACE': r'\s', 'EOF': r'\$', 'EPSILON': r'\ε',
}

def tokenize(input_string):
    global mensajeERROR, texto
    tokens = []
    while input_string:
        match = None
        # Primero intenta coincidir con palabras clave y símbolos
        for token_type, token_regex in TOKEN_TYPES.items():
            if token_type in ['WHITESPACE', 'LETTER', 'NUMBER', 'IGUAL']:
                continue  # Estos se manejan más tarde

            regex_match = re.match(token_regex, input_string)
            if regex_match:
                match = regex_match
                tokens.append(Token(token_type, regex_match.group(0)))
                break


        # Luego intenta coincidir con letras y números
        if not match:
            for token_type in ['LETTER', 'NUMBER', 'WHITESPACE', 'IGUAL']:
                regex_match = re.match(TOKEN_TYPES[token_type], input_string)
                if regex_match:
                    match = regex_match
                    if token_type != 'WHITESPACE':
                        tokens.append(Token(token_type, regex_match.group(0)))
                    break

        if not match:
                mensajeERROR = f"Error en el caracer: {input_string[0]}"
                return render_template('formulario.html', bandera=False, texto=texto, pila=pila, mensajeERROR=mensajeERROR)

        input_string = input_string[match.end():]

    tokens.append(Token('EOF', '$'))
    return tokens

class SimpleParser:
    global mensajeERROR, texto
   
    def __init__(self, input_string):
        self.tokens = tokenize(input_string)  # Convertir la cadena de entrada en tokens  

        try:          
            self.tokens.append(Token('EOF', '$'))  # Agregar un token de fin de archivo al final
        except:
            return render_template('formulario.html', bandera=False, texto=texto, pila=pila, mensajeERROR=mensajeERROR)
        self.stack = ['$', 'start']  # Inicializar la pila con el símbolo de inicio y fin.
        self.pointer = 0  # Establecer el apuntador a la lista de tokens.
        
    def parse(self):
        global mensajeERROR, bandera2

        flag = False

        while True:  # Mientras el tope de la pila no sea el símbolo de fin
            top = self.stack[-1]  # Observamos el símbolo de la cima de la pila
            current_token = self.tokens[self.pointer]

            #print("tokens: ", self.tokens)

            #print(f"Top de la pila: {top}, Token actual: {current_token}, Posición: {self.pointer}")
            #print("~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.")
            #print(self.stack)
            pila.append(self.stack.copy())
            #print("~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.~.")

            print("top de la pila: ", top)
            print("len: ", len(self.stack))

            if self.stack[-1] == '$':
                if any(token.tipo == 'PESO' for token in self.tokens):
                    mensajeERROR = "Error: token PESO ($) detectado en la entrada."
                    self.error(mensajeERROR)
                else:
                    print("Análisis completado correctamente.")
                    break

            if self.stack[-1] == "'":
                if sum(token.tipo == 'COM' for token in self.tokens) > 2 and flag:
                    mensajeERROR = "Error: token COM (') detectado en la entrada."
                    self.error(mensajeERROR)
                flag = True

            if self.is_terminal(top):
                if top == current_token.tipo:  # Comparamos el tipo del token
                    print("es terminal", top)
                    self.stack.pop()  # Extraemos X de la pila
                    pila.append(self.stack.copy())
                    self.pointer += 1  # Avanzamos al siguiente token
                else:
                    self.error("Error de sintaxis")
            elif top == 'EPSILON':  # Si el top de la pila es EPSILON, simplemente lo removemos.
                self.stack.pop()
                pila.append(self.stack.copy())
                #self.pointer += 1  # Avanzamos al siguiente token
                continue
            else:
                print("imprimiendo top para get", top)
                production = self.get_production(top, current_token.tipo)
                if production:
                    self.stack.pop()  # Extraemos X de la pila
                    self.push_production(production)
                else:
                    #self.error("Error de producción")
                    continue

    def peek_next_token(self):
        if self.pointer + 1 < len(self.tokens):
            return self.tokens[self.pointer + 1]
        else:
            return Token('EOF', '$')  # Devuelve un token de fin de archivo si no hay más tokens

    def is_terminal(self, token_type):
            # Lista de tipos de tokens que son terminales
            terminals = [
                "DELETE", "FROM", "LETTER", "WHERE", "COM", "PESO", "IGUAL", "NUMBER",
            ]

            #print(token_type in terminals)

            return token_type in terminals

    def get_production(self, non_terminal, current_token):
        clave = (non_terminal, current_token)
        production = tabla_predictiva.get(clave)

        print("imprimiendo clave a buscar: ", clave)

        if production:
            # La producción se encontró en la tabla predictiva
            return production
        else:
            # Manejo de errores o casos en que no se encuentra una producción
            self.error(f"No se encontró producción para {non_terminal} con token {current_token}")
            return None


    def push_production(self, production):
        # La producción es una lista de símbolos (tipos de tokens o no terminales) a ser añadidos a la pila.
        for symbol in reversed(production):
                self.stack.append(symbol)

    def error(self, message):
        global mensajeERROR
        if self.pointer < len(self.tokens):
            current_token = self.tokens[self.pointer]
            raise SyntaxError(f"{message} en la posición {self.pointer} (Token: {current_token.tipo}, Valor: '{current_token.valor}')")
        else:
            print("errorsito 4")
            raise SyntaxError(f"{message} al final de la entrada")

@app.route('/procesar_formulario', methods=['POST'])
def procesar_formulario():
    global mensajeERROR, bandera2
    texto = request.form.get('texto')

    try:
        parser = SimpleParser(texto)
    except:
        print("errorsito")
        return render_template('formulario.html', bandera2=False, texto=texto, pila=pila, mensajeERROR=mensajeERROR)

    try:
        parser.parse()
        bandera2 = True
        mensajeERROR = ""
    except SyntaxError as e:
        bandera2 = False
        print("errorsito 2")
        mensajeERROR = f"Error en el análisis: {e}"

    if bandera2:
        return render_template('formulario.html', bandera2=True, texto=texto, pila=pila, mensajeERROR="")
    else:
        return render_template('formulario.html', bandera2=False, texto=texto, pila=pila, mensajeERROR=mensajeERROR)

if __name__ == '__main__':
    app.run(debug=False)
