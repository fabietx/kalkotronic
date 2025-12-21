I wanted to create a custom integration for Home Assistant to monitor a Kalkotronic water softener.
This device is manufactured by a leading Italian company in water treatment solutions.

Unfortunately, I don't have a great deal of programming experience, so I started writing the integration using ChatGPT.
The repository is public, and anyone with more skills than me who wants to contribute is welcome.

Basic integration idea:

The device's electronic board uses an ESP32 chip to expose a small web server that reports some diagnostic data about the system.
The integration via scraping should extract the information and write it to home assistant sensors.

https://www.kalkotronic.com/
