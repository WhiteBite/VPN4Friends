#!/usr/bin/env python3
"""Check database for users with VPN profiles."""

import sqlite3
import json

conn = sqlite3.connect('vpn_bot.db')
cursor = conn.cursor()

# Get total users
cursor.execute('SELECT COUNT(*) FROM users')
total = cursor.fetchone()[0]

# Get users with VPN
cursor.execute('SELECT COUNT(*) FROM users WHERE vless_profile_data IS NOT NULL')
with_vpn = cursor.fetchone()[0]

print(f'Total users: {total}')
print(f'Users with VPN: {with_vpn}')

# Get user details
cursor.execute('SELECT telegram_id, username, full_name, vless_profile_data FROM users WHERE vless_profile_data IS NOT NULL')
users = cursor.fetchall()

print('\nUsers with VPN profiles:')
for u in users:
    telegram_id, username, full_name, profile_data = u
    print(f'\n  Telegram ID: {telegram_id}')
    print(f'  Username: @{username or "no_username"}')
    print(f'  Full Name: {full_name}')
    
    if profile_data:
        try:
            profile = json.loads(profile_data)
            print(f'  Email: {profile.get("email", "N/A")}')
            print(f'  Client ID: {profile.get("client_id", "N/A")[:20]}...')
        except:
            print(f'  Profile data: {profile_data[:50]}...')

conn.close()
