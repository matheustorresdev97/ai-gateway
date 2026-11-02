#!/usr/bin/env bash
# Sobe o gateway com o config.yaml desta pasta.
cd "$(dirname "$0")" && exec ../_comum/iniciar_proxy.sh "$PWD/config.yaml"
