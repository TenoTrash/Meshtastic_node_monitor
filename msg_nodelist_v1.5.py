# Comunidad Meshtastic Argentina - Unite por Telegram en https://t.me/meshtastic_argentina
# by Teno - @endif_ok - para Ekoparty 2025
# Monitor de nodos Meshtastic - Últimos 40 nodos
# Y últimos 7 mensajes de los canales configurados en el nodos o directos
# Odio programar en Python así que se bancan la que venga y si no lo hacen ustedes de cero

import meshtastic
import meshtastic.serial_interface
from datetime import datetime, timezone
import time
import os
from pubsub import pub

# Códigos de color ANSI
COLOR_RED = "\033[91m"
COLOR_GREEN = "\033[92m"
COLOR_YELLOW = "\033[93m"
COLOR_BLUE = "\033[94m"
COLOR_MAGENTA = "\033[95m"
COLOR_CYAN = "\033[96m"
COLOR_WHITE = "\033[97m"
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"

# Variables globales
last_messages = []
interface = None

def on_receive(packet, interface):
    """Callback para recibir mensajes"""
    global last_messages
    
    try:
        if packet['decoded']['portnum'] == 'TEXT_MESSAGE_APP':
            message = packet['decoded']['payload'].decode('utf-8')
            from_node = packet['fromId']
            
            # Obtener información del nodo remitente
            node_info = interface.nodes.get(from_node, {})
            user_info = node_info.get('user', {})
            shortname = user_info.get('shortName', 'Unknown')
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            # Crear el mensaje
            new_msg = {
                'time': timestamp,
                'from': shortname,
                'text': message
            }
            
            # Agregar a la lista y mantener solo los últimos 7
            last_messages.append(new_msg)
            if len(last_messages) > 7:
                last_messages.pop(0)
                
            print(f"{COLOR_GREEN}Nuevo mensaje recibido: {shortname}: {message}{COLOR_RESET}")
            
    except (KeyError, UnicodeDecodeError, AttributeError):
        pass  # Ignorar errores comunes silenciosamente
    except Exception as e:
        print(f"{COLOR_RED}Error en on_receive: {e}{COLOR_RESET}")

def setup_interface(serial_port='/dev/ttyACM0'):
    """Configura la interfaz con el callback de mensajes"""
    global interface
    try:
        interface = meshtastic.serial_interface.SerialInterface(serial_port)
        
        # Suscribirse a la recepción de mensajes
        pub.subscribe(on_receive, "meshtastic.receive")
        return True
    except Exception as e:
        print(f"{COLOR_RED}Error configurando interfaz: {e}{COLOR_RESET}")
        return False

def force_node_list_update():
    """Fuerza la actualización de la lista de nodos usando métodos internos"""
    global interface
    
    if interface is None:
        return False
        
    try:
        # Esta parte es la que más me costó hacer
        # Así que valoren manga de lectores
        if hasattr(interface, 'nodes'):
            # Forzar una actualización interna del estado de los nodos
            interface._getMyNodeInfo()
            return True
    except Exception as e:
        # Silenciar errores, no queremos interrumpir el flujo
        pass
    
    return False

def get_node_list():
    """Obtiene y ordena la lista de nodos por última escucha"""
    global interface
    
    if interface is None:
        return []
        
    try:
        # Forzar actualización de la lista de nodos antes de obtenerla
        force_node_list_update()
        
        nodes = []
        
        # Obtener todos los nodos de la interfaz
        for node_id, node_data in interface.nodes.items():
            try:
                # Verificar que el nodo tiene información de usuario
                if 'user' in node_data and node_data['user']:
                    user_info = node_data['user']
                    
                    # Obtener lastHeard de manera segura
                    last_heard = node_data.get('lastHeard', 0)
                    if last_heard is None:
                        last_heard = 0
                    
                    # Incluir todos los nodos, incluso si no han sido escuchados recientemente
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
        
        # Ordenar por lastHeard (más reciente primero)
        # Si lastHeard es 0, se considerará como muy antiguo y aparecerá al final
        nodes.sort(key=lambda x: x['lastHeard'] or 0, reverse=True)
        
        return nodes[:40]  # Devolver solo los primeros 40
        
    except Exception as e:
        print(f"{COLOR_RED}Error obteniendo lista de nodos: {e}{COLOR_RESET}")
        return []

def print_nodes_two_columns(nodes):
    """Muestra la lista de nodos en dos columnas"""
    if not nodes:
        print(f"   {COLOR_YELLOW}No hay nodos disponibles para mostrar{COLOR_RESET}")
        return
    
    # Dividir la lista en dos columnas
    mid_point = (len(nodes) + 1) // 2
    left_column = nodes[:mid_point]
    right_column = nodes[mid_point:]
    
    # Encabezados de columnas
    header_left = f"{COLOR_CYAN}{'':<6} {'Nombre':<20} {'Visto':<10}{COLOR_RESET}"
    header_right = f"{COLOR_CYAN}{'':<6} {'Nombre':<20} {'Visto':<10}{COLOR_RESET}"
    
    # Agregar 3 espacios de indentación
    indent = "   "
    print(f"{indent}{header_left:<36}      {header_right}")
    print(f"{indent}{COLOR_BLUE}{'-' * 36}      {'-' * 36}{COLOR_RESET}")
    
    # Imprimir filas
    max_rows = max(len(left_column), len(right_column))
    for i in range(max_rows):
        # Columna izquierda
        left_line = ""
        if i < len(left_column):
            left_node = left_column[i]
            
            # Formatear timestamp
            last_heard_str_left = "Nunca"
            if left_node['lastHeard'] and left_node['lastHeard'] > 0:
                try:
                    last_heard_left = datetime.fromtimestamp(left_node['lastHeard'], tz=timezone.utc)
                    last_heard_str_left = last_heard_left.strftime("%m-%d %H:%M")
                except (ValueError, OSError):
                    last_heard_str_left = "Error"
            
            short_name_left = left_node['user'].get('shortName', 'N/A')[:6]
            long_name_left = left_node['user'].get('longName', 'N/A')[:18]
            
            # Color para la primera fila (nodo propio)
            if i == 0:
                row_color = COLOR_RED
            else:
                row_color = COLOR_WHITE if i % 2 == 0 else COLOR_YELLOW
                
            left_line = f"{row_color}{short_name_left:<6} {long_name_left:<20} {last_heard_str_left:<10}{COLOR_RESET}"
        
        # Columna derecha
        right_line = ""
        if i < len(right_column):
            right_node = right_column[i]
            
            # Formatear timestamp
            last_heard_str_right = "Nunca"
            if right_node['lastHeard'] and right_node['lastHeard'] > 0:
                try:
                    last_heard_right = datetime.fromtimestamp(right_node['lastHeard'], tz=timezone.utc)
                    last_heard_str_right = last_heard_right.strftime("%m-%d %H:%M")
                except (ValueError, OSError):
                    last_heard_str_right = "Error"
            
            short_name_right = right_node['user'].get('shortName', 'N/A')[:6]
            long_name_right = right_node['user'].get('longName', 'N/A')[:18]
            
            row_color = COLOR_WHITE if i % 2 == 0 else COLOR_YELLOW
            right_line = f"{row_color}{short_name_right:<6} {long_name_right:<20} {last_heard_str_right:<10}{COLOR_RESET}"
        
        # Agregar 3 espacios de indentación a cada fila
        print(f"{indent}{left_line:<36}      {right_line}")

def print_last_messages():
    """Muestra los últimos 7 mensajes recibidos"""
    global last_messages
    
    print(f"\n{COLOR_BLUE}{'-' * 80}{COLOR_RESET}")
    print(f"{COLOR_CYAN}{COLOR_BOLD}Últimos mensajes:{COLOR_RESET}")
    
    if not last_messages:
        print(f"{COLOR_YELLOW}No hay mensajes recientes{COLOR_RESET}")
        return
    
    # Mostrar los mensajes en orden cronológico (más reciente al final)
    for i, msg in enumerate(last_messages):
        msg_color = COLOR_WHITE if i % 2 == 0 else COLOR_YELLOW
        print(f"{msg_color}[{msg['time']}] De {msg['from']}: {msg['text']}{COLOR_RESET}")

def main():
    """Loop principal que se refresca cada 15 segundos"""
    global interface
    
    serial_port = '/dev/ttyACM0'  # Ajusta según el SO
    
    # Mostrar leyendas iniciales
    print(f"{COLOR_BOLD}{COLOR_MAGENTA}Comunidad Meshtastic Argentina - Unite por Telegram en https://t.me/meshtastic_argentina{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_YELLOW}                  by Teno - @endif_ok - para Ekoparty 2025{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}                    Monitor de nodos Meshtastic{COLOR_RESET}")
    
    # Configurar la interfaz con callback de mensajes
    if not setup_interface(serial_port):
        print(f"{COLOR_RED}No se pudo conectar al dispositivo Meshtastic.{COLOR_RESET}")
        print(f"{COLOR_YELLOW}Asegúrate de que el puerto {serial_port} es correcto.{COLOR_RESET}")
        print(f"{COLOR_YELLOW}En Windows podría ser COM3, COM4, etc.{COLOR_RESET}")
        return
    
    print(f"{COLOR_GREEN}Conectado a Meshtastic. Escuchando mensajes...{COLOR_RESET}\n")
    print(f"{COLOR_YELLOW}Presiona Ctrl+C para salir{COLOR_RESET}")
    
    try:
        while True:
            os.system('clear')
            
            # Mostrar leyendas en cada actualización
            print(f"{COLOR_BOLD}{COLOR_MAGENTA}|==========================================================================================|{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_MAGENTA}| Comunidad Meshtastic Argentina - Unite por Telegram en https://t.me/meshtastic_argentina |{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_YELLOW}|                     by Teno - @endif_ok - para Ekoparty 2025                             |{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_CYAN}|                           Monitor de nodos Meshtastic v1.5                               |{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_MAGENTA}|==========================================================================================|{COLOR_RESET}")
            
            # Obtener y mostrar lista de nodos actualizada (forzada)
            nodes = get_node_list()
            # print(f"\n{COLOR_CYAN}Nodos con actividad:{COLOR_RESET}")
            print_nodes_two_columns(nodes)
            
            # Mostrar mensajes
            print_last_messages()
            
            # Mostrar información de actualización
            current_time = datetime.now().strftime("%H:%M:%S")
            # print(f"\n{COLOR_YELLOW}Última actualización: {current_time} - Próxima en 15 segundos...{COLOR_RESET}")
            # print(f"{COLOR_GREEN}Modo pasivo: No se envía ningún mensaje a la red{COLOR_RESET}")
            # print(f"{COLOR_GREEN}Actualización forzada de lista de nodos{COLOR_RESET}")
            
            # Espera 15 segundos
            time.sleep(15)
                
    except KeyboardInterrupt:
        print(f"\n\n{COLOR_RED}Saliendo del monitor...{COLOR_RESET}")
        if interface:
            interface.close()

if __name__ == "__main__":
    main()
