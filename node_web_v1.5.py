import meshtastic
import meshtastic.serial_interface
from datetime import datetime, timezone, timedelta
import time
import os
from pubsub import pub
from flask import Flask, render_template_string, send_from_directory
import threading

COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_WHITE = "\033[97m"
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"

last_messages = []
interface = None
current_nodes = []
app = Flask(__name__)

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor Meshtastic</title>
    <style>
        body {
            background-color: #0f1a25;
            color: #e0e0e0;
            font-family: 'Courier New', monospace;
            margin: 0;
            padding: 15px;
            font-size: 12px;
        }
        .header {
            background: linear-gradient(135deg, #2d5a7c 0%, #4a8c66 100%);
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 15px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            font-size: 12px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            border: 1px solid #3a7a5c;
        }
        .header-content {
            flex: 1;
            text-align: center;
        }
        .header h1 {
            margin: 5px 0;
            font-size: 22px;
            color: #ffffff;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            font-weight: bold;
        }
        .header p {
            margin: 3px 0;
            font-size: 11px;
            color: #c8e6c9;
        }
        .logo-container, .qr-container {
            flex: 0 0 auto;
            display: flex;
            align-items: center;
        }
        .logo-container {
            justify-content: flex-start;
        }
        .qr-container {
            justify-content: flex-end;
        }
        .logo-img, .qr-img {
            max-height: 80px;
            max-width: 80px;
            border-radius: 5px;
            border: 2px solid #3a7a5c;
            background: #1a2e3b;
        }
        .container {
            display: flex;
            flex-wrap: wrap;
            gap: 15px;
        }
        .panel {
            flex: 1;
            min-width: 280px;
            background: #1a2e3b;
            border-radius: 8px;
            padding: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            border: 1px solid #2d5a7c;
        }
        .panel h2 {
            margin-top: 0;
            font-size: 14px;
            color: #4caf82;
            border-bottom: 1px solid #2d5a7c;
            padding-bottom: 5px;
        }
        .nodes-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
            font-size: 11px;
        }
        .node-column {
            background: #223344;
            padding: 8px;
            border-radius: 5px;
            border: 1px solid #2d5a7c;
        }
        .node-row {
            display: flex;
            justify-content: space-between;
            padding: 4px 0;
            border-bottom: 1px solid #2d5a7c;
            font-size: 10px;
        }
        .node-row:first-child {
            color: #4caf82;
            font-weight: bold;
            border-bottom: 2px solid #4caf82;
            font-size: 11px;
        }
        .node-row.own-node {
            color: #ff6b6b;
            font-weight: bold;
        }
        .node-row.even {
            background: #1e2f3c;
        }
        .messages-container {
            max-height: 500px;
            overflow-y: auto;
            font-size: 11px;
        }
        .message {
            padding: 6px;
            margin: 4px 0;
            border-left: 3px solid #4caf82;
            background: #223344;
            font-size: 11px;
            border-radius: 0 4px 4px 0;
        }
        .message:nth-child(even) {
            background: #1e2f3c;
            border-left-color: #2d5a7c;
        }
        .timestamp {
            color: #8ba3b8;
            font-size: 10px;
        }
        .status {
            text-align: center;
            padding: 8px;
            background: #223344;
            border-radius: 5px;
            margin-top: 10px;
            font-size: 11px;
            border: 1px solid #2d5a7c;
            color: #c8e6c9;
        }
        .refresh-info {
            text-align: center;
            color: #4caf82;
            margin-top: 8px;
            font-size: 10px;
        }
        .messages-container::-webkit-scrollbar {
            width: 6px;
        }
        .messages-container::-webkit-scrollbar-track {
            background: #1a2e3b;
        }
        .messages-container::-webkit-scrollbar-thumb {
            background: #2d5a7c;
            border-radius: 3px;
        }
        .messages-container::-webkit-scrollbar-thumb:hover {
            background: #4caf82;
        }
        @media (max-width: 768px) {
            .header {
                flex-direction: column;
            }
            .logo-container, .qr-container {
                justify-content: center;
                margin: 5px 0;
            }
            .logo-img, .qr-img {
                max-height: 60px;
                max-width: 60px;
            }
        }
    </style>
    <meta http-equiv="refresh" content="15">
</head>
<body>
    <div class="header">
        <div class="logo-container">
            <img src="/logo" alt="Logo Meshtastic Argentina" class="logo-img">
        </div>
        
        <div class="header-content">
            <h1>Comunidad Meshtastic Argentina</h1>
            <p>Unite por Telegram: https://t.me/meshtastic_argentina</p>
            <p>by Teno - @endif_ok - para Ekoparty 2025</p>
            <p>Monitor de nodos Meshtastic v1.5 Web</p>
        </div>
        
        <div class="qr-container">
            <img src="/qr" alt="QR Telegram" class="qr-img">
        </div>
    </div>
    
    <div class="container">
        <div class="panel">
            <h2>📡 Nodos Activos</h2>
            <div class="nodes-container">
                <div class="node-column">
                    <div class="node-row">
                        <span>Nombre</span>
                        <span>Visto</span>
                    </div>
                    {% for node in left_column %}
                    <div class="node-row {% if node.is_own %}own-node{% elif loop.index0 % 2 == 0 %}even{% endif %}">
                        <span>{{ node.short_name }} - {{ node.long_name }}</span>
                        <span>{{ node.last_heard }}</span>
                    </div>
                    {% endfor %}
                </div>
                <div class="node-column">
                    <div class="node-row">
                        <span>Nombre</span>
                        <span>Visto</span>
                    </div>
                    {% for node in right_column %}
                    <div class="node-row {% if loop.index % 2 == 0 %}even{% endif %}">
                        <span>{{ node.short_name }} - {{ node.long_name }}</span>
                        <span>{{ node.last_heard }}</span>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        
        <div class="panel">
            <h2>💬 Últimos Mensajes</h2>
            <div class="messages-container">
                {% for message in messages %}
                <div class="message">
                    <span class="timestamp">[{{ message.time }}]</span>
                    <strong>De {{ message.from }}:</strong> {{ message.text }}
                </div>
                {% else %}
                <div class="message">No hay mensajes recientes</div>
                {% endfor %}
            </div>
        </div>
    </div>
    
    <div class="status">
        <p>🔄 Última actualización: {{ current_time }}</p>
    </div>
    
    <div class="refresh-info">
        La página se actualiza automáticamente
    </div>
</body>
</html>
"""

def on_receive(packet, interface):
    global last_messages
    
    try:
        if packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            message = packet['decoded']['payload'].decode('utf-8')
            from_node = packet['fromId']
            
            node_info = interface.nodes.get(from_node, {})
            user_info = node_info.get('user', {})
            shortname = user_info.get('shortName', 'Unknown')
            
            # Hora local Argentina (GMT-3)
            timestamp = datetime.now().astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M:%S")
            
            new_msg = {
                'time': timestamp,
                'from': shortname,
                'text': message
            }
            
            last_messages.append(new_msg)
            if len(last_messages) > 20:
                last_messages.pop(0)
                
            print(f"{COLOR_GREEN}Nuevo mensaje: {shortname}: {message}{COLOR_RESET}")
            
    except (KeyError, UnicodeDecodeError, AttributeError):
        pass
    except Exception as e:
        print(f"{COLOR_RED}Error procesando mensaje: {e}{COLOR_RESET}")

def on_connection(interface, topic=pub.AUTO_TOPIC):
    """Callback cuando se establece la conexión"""
    print(f"{COLOR_GREEN}Conexión establecida con el dispositivo Meshtastic{COLOR_RESET}")

def setup_interface(serial_port='/dev/ttyACM0'):
    """Configura la conexión con el dispositivo Meshtastic"""
    global interface
    try:
        interface = meshtastic.serial_interface.SerialInterface(serial_port)
        
        # Suscribirse a eventos importantes
        pub.subscribe(on_receive, "meshtastic.receive")
        pub.subscribe(on_connection, "meshtastic.connection.established")
        
        print(f"{COLOR_GREEN}Interfaz configurada correctamente{COLOR_RESET}")
        return True
    except Exception as e:
        print(f"{COLOR_RED}Error de conexión: {e}{COLOR_RESET}")
        return False

def get_node_list():
    """Obtiene y ordena los nodos por última actividad - Modo completamente pasivo"""
    global interface
    
    if interface is None:
        print(f"{COLOR_YELLOW}Interfaz no disponible{COLOR_RESET}")
        return []
        
    try:
        nodes = []
        node_count = 0
        
        # Método pasivo: solo leer la información disponible
        for node_id, node_data in interface.nodes.items():
            node_count += 1
            try:
                if 'user' in node_data and node_data['user']:
                    user_info = node_data['user']
                    
                    last_heard = node_data.get('lastHeard', 0)
                    if last_heard is None:
                        last_heard = 0
                    
                    node_info = {
                        'user': {
                            'shortName': user_info.get('shortName', 'Desconocido'),
                            'longName': user_info.get('longName', 'Desconocido')
                        },
                        'lastHeard': last_heard
                    }
                    nodes.append(node_info)
            except (KeyError, AttributeError):
                continue
        
        print(f"{COLOR_CYAN}Nodos encontrados: {node_count}{COLOR_RESET}")
        
        # Ordenar por última vez escuchado (más reciente primero)
        nodes.sort(key=lambda x: x['lastHeard'] or 0, reverse=True)
        return nodes[:30]
        
    except Exception as e:
        print(f"{COLOR_RED}Error obteniendo nodos: {e}{COLOR_RESET}")
        return []

def update_node_data():
    """Actualiza periódicamente la lista de nodos de forma pasiva"""
    global current_nodes
    while True:
        try:
            new_nodes = get_node_list()
            if new_nodes:
                current_nodes = new_nodes
                print(f"{COLOR_GREEN}Lista de nodos actualizada: {len(current_nodes)} nodos{COLOR_RESET}")
            else:
                print(f"{COLOR_YELLOW}No se pudieron obtener nodos{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_RED}Error en actualización de nodos: {e}{COLOR_RESET}")
        
        time.sleep(15)

def format_nodes_for_web(nodes):
    """Prepara los datos de nodos para mostrar en la web"""
    formatted_nodes = []
    
    # Zona horaria Argentina (GMT-3)
    argentina_tz = timezone(timedelta(hours=-3))
    
    for i, node in enumerate(nodes):
        last_heard_str = "Nunca"
        if node['lastHeard'] and node['lastHeard'] > 0:
            try:
                # Convertir UTC a GMT-3
                last_heard_utc = datetime.fromtimestamp(node['lastHeard'], tz=timezone.utc)
                last_heard_arg = last_heard_utc.astimezone(argentina_tz)
                last_heard_str = last_heard_arg.strftime("%m-%d %H:%M")
            except (ValueError, OSError):
                last_heard_str = "Error"
        
        short_name = node['user'].get('shortName', 'N/A')[:6]
        long_name = node['user'].get('longName', 'N/A')[:25]
        
        formatted_nodes.append({
            'short_name': short_name,
            'long_name': long_name,
            'last_heard': last_heard_str,
            'is_own': i == 0
        })
    
    return formatted_nodes

@app.route('/')
def index():
    """Página principal con el monitor de nodos y mensajes"""
    global current_nodes, last_messages
    
    formatted_nodes = format_nodes_for_web(current_nodes)
    
    mid_point = (len(formatted_nodes) + 1) // 2
    left_column = formatted_nodes[:mid_point]
    right_column = formatted_nodes[mid_point:]
    
    # Hora actual en GMT-3
    current_time = datetime.now().astimezone(timezone(timedelta(hours=-3))).strftime("%H:%M:%S")
    
    return render_template_string(HTML_TEMPLATE,
                                left_column=left_column,
                                right_column=right_column,
                                messages=last_messages,
                                current_time=current_time,
                                node_count=len(current_nodes))

@app.route('/logo')
def serve_logo():
    return send_from_directory('.', 'logo_mesharg_imprimir.png')

@app.route('/qr')
def serve_qr():
    return send_from_directory('.', 'QR.png')

def main():
    """Función principal que inicia el servidor web"""
    global interface
    
    serial_port = '/dev/ttyACM0'
    
    print(f"{COLOR_BOLD}{COLOR_CYAN}Comunidad Meshtastic Argentina - https://t.me/meshtastic_argentina{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_GREEN}by Teno - @endif_ok - Ekoparty 2025{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}Monitor Meshtastic - Web Server (Modo Pasivo){COLOR_RESET}")
    
    if not setup_interface(serial_port):
        print(f"{COLOR_RED}No se pudo conectar al dispositivo.{COLOR_RESET}")
        print(f"{COLOR_YELLOW}Verifica el puerto: {serial_port}{COLOR_RESET}")
        print(f"{COLOR_YELLOW}En Windows usa: COM3, COM4, etc.{COLOR_RESET}")
        return
    
    print(f"{COLOR_GREEN}Conectado a Meshtastic. Iniciando servidor web...{COLOR_RESET}")
    print(f"{COLOR_YELLOW}Servidor disponible en: http://localhost:5000{COLOR_RESET}")
    print(f"{COLOR_GREEN}Modo 100% pasivo - No se envía tráfico a la red{COLOR_RESET}")
    print(f"{COLOR_YELLOW}Presiona Ctrl+C para detener{COLOR_RESET}")
    
    # Obtener lista inicial de nodos
    print(f"{COLOR_CYAN}Obteniendo lista inicial de nodos...{COLOR_RESET}")
    initial_nodes = get_node_list()
    if initial_nodes:
        current_nodes = initial_nodes
        print(f"{COLOR_GREEN}Nodos iniciales cargados: {len(current_nodes)}{COLOR_RESET}")
    
    # Iniciar hilo de actualización
    update_thread = threading.Thread(target=update_node_data, daemon=True)
    update_thread.start()
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print(f"\n{COLOR_RED}Deteniendo servidor...{COLOR_RESET}")
        if interface:
            interface.close()

if __name__ == "__main__":
    main()
