#!/bin/bash

echo "copy /etc/dhcpcd.conf"
cp /etc/dhcpcd.conf "/etc/dhcpcd.conf-$(date +"%m-%d-%y-%r")"
cp dhcpcd.conf /etc

echo "copy /etc/dnsmasq.conf"
cp /etc/dnsmasq.conf "/etc/dnsmasq.conf-$(date +"%m-%d-%y-%r")"
cp dnsmasq.conf /etc

echo "copy /etc/hostapd/hostapd.conf"
cp /etc/hostapd/hostapd.conf "/etc/hostapd/hostapd.conf-$(date +"%m-%d-%y-%r")"
cp hostapd.conf /etc/hostapd

echo "copy /etc/default/hostapd"
cp /etc/default/hostapd "/etc/default/hostapd-$(date +"%m-%d-%y-%r")"
cp hostapd /etc/default
