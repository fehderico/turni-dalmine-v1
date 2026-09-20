# Mappatura del modulo UNICA

Il prototipo riconosce automaticamente un export Excel del foglio risposte Google Forms.

| Campo del modulo | Campo interno | Regola |
|---|---|---|
| Email | chiave medico | normalizzata in minuscolo; l'ultima risposta prevale |
| COGNOME / NOME | anagrafica | obbligatori, usati negli output |
| ASST DI APPARTENENZA | gruppo di priorità | OVEST, BGEST, ALTRI |
| Griglia fine settimana | disponibilità | data dalla riga, turno dalla selezione |
| Griglia feriali | disponibilità | data dalla riga, turno dalla selezione |
| Contratto in periferica | stato contratto | riportato negli output, non usato dall'algoritmo V1 |
| Note | note | riportate nel riepilogo medici |

## Turni

| Modulo | Codice | Capacità |
|---|---|---:|
| 8-14 | MAT | 8 |
| 14-20 | POM | 8 |
| 8-20 | DIU | 7 |
| 19-00 | SER | 7 |
| 20-8 | NOT | 5 |

## Decisioni e dati mancanti

- I minimi e le informazioni contrattuali non entrano nella decisione della V1.
- La precedenza ASST preferisce gli assegnamenti OVEST e poi BGEST a copertura totale invariata.
- Le intestazioni delle griglie stabiliscono quali fasce devono esistere in ogni data, incluse festività e prefestivi infrasettimanali.
- I turni periferici non sono inclusi nell'export. Per controllare automaticamente le 11 ore fra periferica e UNICA servirà in futuro un secondo input con medico, inizio e fine dei turni periferici.
