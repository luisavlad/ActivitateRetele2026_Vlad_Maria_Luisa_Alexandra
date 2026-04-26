import socket

HOST        = '127.0.0.1'
PORT        = 9999
BUFFER_SIZE = 1024

clienti_conectati = {}
mesaje = {}
contor_id = 0

server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server_socket.bind((HOST, PORT))

print("=" * 50)
print(f"  SERVER UDP pornit pe {HOST}:{PORT}")
print("  Asteptam mesaje de la clienti...")
print("=" * 50)

while True:
    try:
        date_brute, adresa_client = server_socket.recvfrom(BUFFER_SIZE)
        mesaj_primit = date_brute.decode('utf-8').strip()

        parti = mesaj_primit.split(' ', 1)
        comanda = parti[0].upper()
        argumente = parti[1] if len(parti) > 1 else ''

        print(f"\n[PRIMIT] De la {adresa_client}: '{mesaj_primit}'")

        if comanda == 'CONNECT':
            if adresa_client in clienti_conectati:
                raspuns = "EROARE: Esti deja conectat la server."
            else:
                clienti_conectati[adresa_client] = True
                nr_clienti = len(clienti_conectati)
                raspuns = f"OK: Conectat cu succes. Clienti activi: {nr_clienti}"
                print(f"[SERVER] Client nou conectat: {adresa_client}")

        elif comanda == 'DISCONNECT':
            if adresa_client in clienti_conectati:
                del clienti_conectati[adresa_client]
                raspuns = "OK: Deconectat cu succes. La revedere!"
                print(f"[SERVER] Client deconectat: {adresa_client}")
            else:
                raspuns = "EROARE: Nu esti conectat la server."

        elif comanda == 'PUBLISH':
            if adresa_client not in clienti_conectati:
                raspuns = "EROARE: Nu esti conectat la server."
            elif not argumente.strip():
                raspuns = "EROARE: Mesajul nu poate fi gol."
            else:
                contor_id += 1
                mesaje[contor_id] = {'text': argumente.strip(), 'autor': adresa_client}
                raspuns = f"OK: Mesaj publicat cu ID={contor_id}"
                print(f"[SERVER] Mesaj nou (ID={contor_id}) de la {adresa_client}: '{argumente.strip()}'")

        elif comanda == 'DELETE':
            if adresa_client not in clienti_conectati:
                raspuns = "EROARE: Nu esti conectat la server."
            else:
                try:
                    id_cerut = int(argumente.strip())
                except ValueError:
                    id_cerut = None
                if id_cerut is None:
                    raspuns = "EROARE: ID-ul trebuie sa fie un numar intreg."
                elif id_cerut not in mesaje:
                    raspuns = f"EROARE: Nu exista mesaj cu ID={id_cerut}."
                elif mesaje[id_cerut]['autor'] != adresa_client:
                    raspuns = f"EROARE: Nu esti autorul mesajului cu ID={id_cerut}."
                else:
                    del mesaje[id_cerut]
                    raspuns = f"OK: Mesajul cu ID={id_cerut} a fost sters."
                    print(f"[SERVER] Mesaj sters (ID={id_cerut}) de catre {adresa_client}")

        elif comanda == 'LIST':
            if adresa_client not in clienti_conectati:
                raspuns = "EROARE: Nu esti conectat la server."
            elif not mesaje:
                raspuns = "OK: Nu exista mesaje publicate."
            else:
                linii = [f"ID={mid}: {m['text']}" for mid, m in mesaje.items()]
                raspuns = "OK: " + " | ".join(linii)

        else:
            raspuns = f"EROARE: Comanda '{comanda}' este necunoscuta. Comenzi valide: CONNECT, DISCONNECT, PUBLISH, DELETE, LIST"

        server_socket.sendto(raspuns.encode('utf-8'), adresa_client)
        print(f"[TRIMIS]  Catre {adresa_client}: '{raspuns}'")

    except KeyboardInterrupt:
        print("\n[SERVER] Oprire server...")
        break
    except Exception as e:
        print(f"[EROARE] {e}")

server_socket.close()
print("[SERVER] Socket inchis.")
