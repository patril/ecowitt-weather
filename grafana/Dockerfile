FROM grafana/grafana:13.2.0

ENV GF_PATHS_PLUGINS=/var/lib/grafana-plugins

USER root
RUN mkdir -p "$GF_PATHS_PLUGINS" && chown -R grafana:0 "$GF_PATHS_PLUGINS"

USER grafana
RUN grafana cli --pluginsDir "$GF_PATHS_PLUGINS" plugins install oceandatatools-compass-panel 2.1.3 \
    && grafana cli --pluginsDir "$GF_PATHS_PLUGINS" plugins install briangann-gauge-panel 2.2.0
