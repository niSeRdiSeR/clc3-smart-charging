# CLC3: PV Smart Charging

## Idee
Der Plan ist, PV-Energie durch sogenanntes PV-Überschuss-Laden
möglichst effizient zu nutzen, indem man versucht, den Verbrauch mittels variabler
Lade-Geschwindigkeit an einem Ladegerät für E-Fahrzeuge periodisch an die
Erzeugung anzupassen. Die Strategie dahinter ist dabei die absolute Differenz
zwischen Produktion und Verbrauch so gering wie möglich zu halten, um
Energie-Zukauf, aber auch (tendenziell schlecht vergütete) Einspeisung zu
vermeiden. \
Zwar existieren bei den meisten Herstellern proprietäre Systemlösungen um den
PV-Überschuss möglichst intelligent einzusetzen, diese erfordern allerdings natürlich
auch, dass sämtliche verwendete Geräte desselben Herstellers (oft auch in der
passenden Revision) vorhanden sind. Dies führt in der Praxis zu mehreren
Einschränkungen, sodass es ohne eigener Lösung meistens Zwangsläufig zu einer
Kompromissentscheidung beim Kauf der benutzten Geräte kommt, da speziell bei
PV-Anlagen auch deren Features stark vom Hersteller abhängig und somit teils
extrem unterschiedlich geeignet sind.


## Aufgabenstellung/Ziel
In diesem Projekt wird dazu ein SolarEdge-Wechselrichter und ein
Fronius-Ladegerät verwendet. Relevante Daten sollen dabei periodisch gesammelt
werden und abhängig davon, das Ladegerät richtig konfiguriert werden.

Da der Fronius-Wattpilot nur über proprietäre Schnittstellen im WWW erreichbar ist, ist es notwendig Werte *Edge*-seitig lokal abzufangen oder zu setzen. Dazu ist ein entsprechender Client zu implementieren, welcher Werte aus Messages aus der Cloud entgegennimmt und Status-Werte in diese pusht. Abgesehen von diesem Edge-Client sind alle anderen Komponenten in der Cloud provisioniert.

Die Werte des Wechselrichters können periodisch über eine dokumentierte REST-API abgefragt werden. Nach jeder Abfrage wird das Stromfluss-Delta (unter Berücksichtigung des zuletzt gemeldeten Eigenverbrauchs des Ladegeräts) berechnet und der Ladestrom angepasst bzw. gestoppt.

Es soll dabei natürlich auch möglich sein, diese Logik zu unterbrechen und volle Ladeleistung zur Verfügung zu stellen, um bei Bedarf auch immer (schnell) laden zu können.

## Lösung
### Architektur
Folgende Architektur wurde in der **Google Cloud** umgesetzt:

![Architektur](./doc/architecture.png)

Grundsätzlich war die Idee, das System Event-getrieben aufzubauen. \
Immer dann, wenn neue Messwerte vom Wechselrichter kommen, soll der Wattpilot den Ladevorgang entsprechend anpassen. Dazu müssen auch aktuelle Ladeinformationen, wie der aktuelle Ladestrom, vom Wattpilot zur Verfügung gestellt werden. Daraus ergeben sich folgende Event-Abläufe:
- **Wechselrichter-Update**: \
  Da Werte aktiv von einer REST-API abgefragt werden müssen, müssen diese Fetches periodisch getriggert werden. \
  Um den Event-getriebenen Ansatz möglichst beizubehalten, wurde dazu der `Cloud-Scheduler` eingesetzt. Mit diesem können periodisch Nachrichten an ein Topic in Google *Cloud Pub/Sub* gepusht werden, wodurch der Ablauf getriggert wird. \
  Der `inverter-fetcher` greift daraufhin die abzufragenden Wechselrichter aus der `Cloud SQL`-DB ab und ruft dessen aktuelle Stromwerte ab. Diese werden anschließend in ein anderes Topic in Pub/Sub publiziert und in einer *InfluxDB2* gespeichert (ebenfalls in der Cloud; siehe unten). \
  Der `inverter-handler` (=Logik) reagiert auf diese Messwerte: Um den Ziel-Ladestrom zu berechnen, werden auch die aktuellen/letzten Werte des Wattpilots benötigt und dazu aus dem Redis-Cache geladen.

- **Wattpilot-Update**: \
  Damit diese Werte auch stets im Redis-Cache verfügbar sind, wird auch Edge-seitig bei relevanten Wertänderungen eine Nachricht in Pub/Sub veröffentlicht. \
  Der `wp-handler` nimmt diese entgegen und aktualisiert den Redis-Cache. Zusätzlich schreibt dieser die Werte zur Dokumentation und Nachvollziehbarkeit in InfluxDB.

#### Django
Django soll als Management/Konfigurations-Möglichkeit dienen. Praktisch ist dabei der integrierte OR-Mapper und vor allem auch eine integrierte Admin-GUI, welche einfache Administration Out-of-the-Box ermöglicht. \
Die Informationen werden dabei in der Klasse `Inverter` (=Wechselrichter) verwaltet, bestehend aus:
- `name: str`
- `token: str`
- `site_id: str`
- `wattpilot_id: int`
- `smart_charging_enabled: bool`

Die Felder `token` und `site_id` werden dabei zum Abfragen der aktuellen Stromwerte benötigt und seitens des Herstellers zur Verfügung gestellt. Die `wattpilot_id` referenziert den vor Ort befindlichen Wattpilot. Einem Wattpilot wird am Edge-Client eine fixe ID vergeben. So können Wattpiloten und Inverter flexibel verbunden werden. 

Django wird dabei als **App-Engine** zur Verfügung gestellt, einem **PaaS**-Dienst.

Man hat hierbei die Möglichkeit, zwischen zwei Varianten zu wählen:
1. **Standard**
   App wird in einer Sandbox bereitgestellt. Läuft kein Traffic, ist auch keine Instanz aktiv und bei erhöhtem Traffic werden automatisch mehrere Instanzen gestartet und Load-Balancing betrieben. \
   *Scale-to-Zero*: Die Startup-Zeit wird seitens Google nur mit "Seconds" angegeben - in der Praxis in diesem Fall meist unter 5 Sekunden. Im Hinblick auf die Kosten ist dies somit eine äußerst wirtschaftliche Lösung, da der Dienst auch nur zu Konfigurationszwecken (also relativ selten) verwendet wird.

2. **Flexibel** \
   Hier wird die App in Docker-Containern zur Verfügung gestellt. Die Startup-Zeit wird hier in "Minuten" angegeben, was *Scale-to-Zero unmöglich* macht und auch nicht von Google unterstüzt wird.

Die Standard-Variante ist in diesem Fall also, speziell für einen Prototyp, besser geeignet. Wäre man an einem Punkt, wo es Sinn machen würde, eine Instanz permanent am laufen zu halten, ist ein Umstieg leicht möglich. Die flexible Variante kann in diesem Fall bis auf den `app.yaml`-File zum Beschreiben der Infrastruktur (*IaC*) analog zur Standard-Variante eingesetzt werden.

Eine alternative Lösung mit ähnlichen Vorteilen wäre auch der Einsatz von *Cloun Run*. In diesem Fall müssen Container-Images zwar vom User selbst erstellt bzw. beschrieben werden, allerdings ist das Start-Verhalten hier laut Google schnell genug, sodass auch hier `Scale-to-Zero` angewandt wird. Hier würde dieser Ansatz allerdings effektiv nur mehr Overhead in Form eines Dockerfiles o.ä. bewirken. 

Google stellt zu diesem Thema sogar spezifisch für Django [Anleitungen](https://cloud.google.com/python/django/appengine) bereit. Hier wird zum Beispiel auch erklärt, wie man eine Datenbankverbindung mit *Cloud SQL* herstellen kann - Sowohl für den Produktiveinsatz, als auch mittels Proxy-Applikation zum lokalen Entwickeln und Migrieren.

### Functions
Sämtliche andere Implementierungen (außer natürlich der Edge-Client und die SaaS-Anwendungen) wurden in Python 3.10 entwickelt und als *Cloud Function* eingesetzt, welche sich für den Event-getriebenen Ansatz - speziell in Kombination mit Pub/Sub - bestens eignen.

Zudem sind Kriterien wie permanente Verfügbarkeit/kurze Startup-Time, Performance und dergleichen in diesem Fall irrelevant. Wichtig ist, dass die Funktion zuverlässig ausgeführt wird, was dank Pub/Sub und automatischen Retries garantiert ist. Mehrfachzustellungen sind ebenfalls unproblematisch, könnten aber auch durch einfache Konfiguration der entsprechenden Pub/Sub-Subscription unkompliziert vermieden werden.

Authentifizierung oder Netzwerkkonfiguration sind im Google-Umfeld in diesem Setup zu vernachlässigen, da in einem Projekt ohnehin ein Default-Netzwerk angelegt wird und die Funktionen durch deren Service-Account auch authentifiziert sind. Es ist allerdings nötig, diesem Service-Account dazu die nötigen Berechtigungen zu geben. Verwendet man für mehrere/alle Functions denselben Service-Account, ist das eine einmalige Angelegenheit.

### Messaging
Wie bereits erwähnt, wird als Messaging-Dienst Googles *Pub/Sub* verwendet, welcher asynchrone Message/Event-Zustellung durch das bekannte und namensgebende Publish/Subscribe-Pattern ermöglicht.

Je nach Subscription-Typ, müssen Nachrichten dabei entweder gepullt werden, oder werden an einen HTTP-Endpunkt gepusht. \
Die `google-cloud-pubsub`-Library, sowie auch die anderer Programmiersprachen, pullen die Nachrichten üblicherweise. Der Push-Typ ist allerdings für das Triggern der Functions geeignet und übergibt die Message als Inhalt im Body des Request.

Für dieses Projekt gelegen kommt zudem die Möglichkeit, Filter für Subscriptions definieren zu können. Damit lässt sich zum Beispiel gewährleisten, dass zu setzende Properties eines Wattpilots auch nur diesen bestimmten Wattpilot erreichen.\
Dazu kann man nach belieben Attribute mit String-Values zur Nachricht hinzufügen, gegen welche gefiltert werden kann.

**Code-Snippets zum gefilterten Publishen/Subscriben**
Zum Publishen können Attribute einfach spezifiziert werden (in diesem Fall via `kwargs`):

```python
data = json.dumps({"pk": pk, "prop": prop, "val": val})
publisher.publish(topic_path, data.encode('utf-8'), pk=f"{pk}")
```

Das Subscriben erfordert für jede(n) Filter(-kombination) eine eigene Subscription. \
Hier wird auf der Edge z.B. überprüft, ob die nötige Subscription bereits existiert und ansonsten automatisch erstellt:
```python
subscription_name = f'projects/{PROJECT_ID}/subscriptions/wp-edge-{WP_PK}T-sub'
project_path = f"projects/{PROJECT_ID}"
print(publisher.list_topic_subscriptions(request={"topic": sub_topic_name}))
for subscription in publisher.list_topic_subscriptions(request={"topic": sub_topic_name}):
    if f'wp-edge-{WP_PK}' in subscription:
        # subscription already exists
        break
else:
    # executing only if no break occured:
    # subscription missing, create new sub
    subscriber.create_subscription(request={"name": subscription_name, "topic": sub_topic_name, "filter": f'attributes.pk = "{WP_PK}"'})
future = subscriber.subscribe(subscription_name, sub_msg_handler)
```
### InfluxDB

### Secrets