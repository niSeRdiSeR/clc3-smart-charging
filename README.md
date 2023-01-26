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
werden und abhängig davon, das Ladegerät richtig konfiguriert werden. \
Da der Fronius-Wattpilot nur über proprietäre Schnittstellen im WWW erreichbar ist, ist es notwendig Werte *Edge*-seitig lokal abzufangen oder zu setzen. Dazu ist ein entsprechender Client zu implementieren, welcher Werte aus Messages aus der Cloud entgegennimmt und Status-Werte in diese pusht. Abgesehen von diesem Edge-Client sind alle anderen Komponenten in der Cloud provisioniert. \
Die Werte des Wechselrichters können periodisch über eine dokumentierte REST-API abgefragt werden. Nach jeder Abfrage wird das Stromfluss-Delta (unter Berücksichtigung des zuletzt gemeldeten Eigenverbrauchs des Ladegeräts) berechnet und der Ladestrom angepasst bzw. gestoppt. \
Es soll dabei natürlich auch möglich sein, diese Logik zu unterbrechen und volle Ladeleistung zur Verfügung zu stellen, um bei Bedarf auch immer (schnell) laden zu können.

## Lösung
### Architektur
### Messaging
### Django-Instanz(en)
### Functions
### InfluxDB