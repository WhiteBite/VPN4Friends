import json


def build_matrix():
    with open("vpn-config.json", encoding="utf-8") as f:
        config = json.load(f)

    stealth_hosts = {
        "moscow": "msk1.whitebite.ru",
        "finland": "fin1.whitebite.ru",
        "germany": "ger1.whitebite.ru",
    }

    # Base panel configs
    panels = {
        "finland": config["nodes"]["finland"]["panel_config"],
        "germany": config["nodes"]["germany"]["panel_config"],
    }

    # We will build combinations for 'finland' and 'germany'
    endpoints = []

    # Definition of available connections
    # (protocol, transport, port, routing_tag, format_name, label_suffix, group, sub_label, emoji)
    conns = {
        "finland": [
            ("vless", "tcp", 443, "direct", "tcp", "Direct", "fast", "⚡", 1),
            ("vless", "tcp", 8446, "warp", "warp", "WARP", "warp", "🎬", 10),
            ("vless", "grpc", 8447, "direct", "grpc", "gRPC", "stealth", "🛡", 20),
            ("vless", "xhttp", 8448, "warp", "xhttp_warp", "xHTTP WARP", "stealth_warp", "🛡🎬", 30),
        ],
        "germany": [
            ("vless", "tcp", 8443, "direct", "tcp", "Direct", "fast", "⚡", 2),
            ("vless", "tcp", 8446, "warp", "warp", "WARP", "warp", "🎬", 11),
            ("vless", "grpc", 8447, "direct", "grpc", "gRPC", "stealth", "🛡", 21),
            ("vless", "xhttp", 8448, "warp", "xhttp_warp", "xHTTP WARP", "stealth_warp", "🛡🎬", 31),
        ],
    }

    # Moscow Relayed ports - we invent sequential ports matching transport if they didn't exist
    # E.g. moscow relay to FI TCP(443) -> 443
    # moscow relay to FI gRPC(8447) -> 444
    # moscow relay to FI WARP TCP(8446) -> 446
    # moscow relay to FI xHTTP(8448) -> 448

    # moscow relay to DE TCP(8443) -> 8445
    # moscow relay to DE WARP TCP(8446) -> 8446?
    # Actually, we will just use the same port on moscow as on the target if possible,
    # except when there are collisions (like BOTH DE and FI use 8446).

    moscow_ports = {
        "finland": {"tcp": 8433, "warp": 8466, "grpc": 8477, "xhttp_warp": 8488},
        "germany": {"tcp": 8445, "warp": 8456, "grpc": 8457, "xhttp_warp": 8458},
    }

    common_keys = {
        "finland": {
            "pbk": "Lv_n3O9Vciye5kY4tOnAUimEg-0apjZRoIshS0j94S0",
            "sid": "***REMOVED***",
        },
        "germany": {
            "pbk": "Lv_n3O9Vciye5kY4tOnAUimEg-0apjZRoIshS0j94S0",
            "sid": config["endpoints"][1].get("sid", "34988d91cdef"),
        },
    }

    def add_endpoint(country, is_relay, proto_config):
        proto, transport, direct_port, rtag, fname, lsuffix, group, emoji, base_sort = proto_config

        ep = {
            "name": f"{country}_{'msk_' if is_relay else ''}{fname}",
            "label": f"{'Финляндия' if country == 'finland' else 'Германия'} ({lsuffix}{' МСК' if is_relay else ''})",
            "category": "vpn",
            "country": "Финляндия" if country == "finland" else "Германия",
            "host": stealth_hosts["moscow"] if is_relay else stealth_hosts[country],
            "port": moscow_ports[country][fname] if is_relay else direct_port,
            "protocol": proto,
            "transport": transport,
            "security": "reality",
            "sni": "max.ru",
            "pbk": common_keys[country]["pbk"],
            "sid": common_keys[country]["sid"],
        }

        # flow
        if transport == "tcp":
            ep["flow"] = "xtls-rprx-vision"

        # service name
        if transport == "grpc":
            ep["serviceName"] = "grpc"

        # path
        if transport == "xhttp":
            ep["path"] = "/xhttp"

        ep["group"] = "moscow" if is_relay else group
        flag = "🇫🇮" if country == "finland" else "🇩🇪"

        # Sub-label
        ep["sub_label"] = (
            f"{emoji if not is_relay else '📱'} {flag} {'Финляндия' if country == 'finland' else 'Германия'} {lsuffix}{' МСК' if is_relay else ''}".replace(
                " Direct", ""
            ).strip()
        )

        ep["sort_order"] = base_sort + (40 if is_relay else 0)

        if is_relay:
            ep["is_relay"] = True
        else:
            ep["routing_tag"] = rtag
            ep["panel_type"] = "3xui"
            ep["panel_config"] = panels[country]

        # Removed hardcoded old pk for Germany, will fallback to global Reality private key

        endpoints.append(ep)

    for c_name, c_list in conns.items():
        for proto_config in c_list:
            # Add Direct
            add_endpoint(c_name, False, proto_config)
            # Add Moscow Relay
            add_endpoint(c_name, True, proto_config)

    # MTProto & SOCKS (Add at the end)
    tg_proxies = [
        {
            "name": "finland_tg_mtproto",
            "label": "FI MTProto Proxy",
            "category": "telegram",
            "country": "Финляндия",
            "host": stealth_hosts["finland"],
            "port": 4443,
            "protocol": "mtproto",
            "transport": "mtproto",
            "secret": "***REMOVED***",
            "visible_in_sub": False,
        },
        {
            "name": "finland_tg_socks",
            "label": "FI SOCKS5 Proxy",
            "category": "telegram",
            "country": "Финляндия",
            "host": stealth_hosts["finland"],
            "port": 1080,
            "protocol": "socks",
            "transport": "socks",
            "panel_config": {"user": "telegram", "pass": "vpn4friends"},
            "visible_in_sub": False,
        },
        {
            "name": "germany_tg_mtproto",
            "label": "DE MTProto Proxy",
            "category": "telegram",
            "country": "Германия",
            "host": stealth_hosts["germany"],
            "port": 4443,
            "protocol": "mtproto",
            "transport": "mtproto",
            "secret": "***REMOVED***",
            "visible_in_sub": False,
        },
        {
            "name": "germany_tg_socks",
            "label": "DE SOCKS5 Proxy",
            "category": "telegram",
            "country": "Германия",
            "host": stealth_hosts["germany"],
            "port": 1080,
            "protocol": "socks",
            "transport": "socks",
            "panel_config": {"user": "telegram", "pass": "vpn4friends"},
            "visible_in_sub": False,
        },
    ]

    endpoints.extend(tg_proxies)

    config["endpoints"] = endpoints

    with open("vpn-config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"Total endpoints generated: {len(endpoints)}")


if __name__ == "__main__":
    build_matrix()
