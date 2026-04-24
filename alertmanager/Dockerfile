# Build on Alpine so we have a shell and envsubst (from gettext)
FROM alpine:3.19

RUN apk add --no-cache gettext curl

# Copy the Alertmanager binary from the official image
COPY --from=prom/alertmanager:v0.27.0 /bin/alertmanager /bin/alertmanager

# Copy the template — the real config is generated at startup
COPY alertmanager.yml.tmpl /etc/alertmanager/alertmanager.yml.tmpl

EXPOSE 9093

# envsubst renders ${ALERTMANAGER_WEBHOOK_URL} into the real config, then starts Alertmanager
ENTRYPOINT ["sh", "-c", \
  "envsubst < /etc/alertmanager/alertmanager.yml.tmpl > /etc/alertmanager/alertmanager.yml && \
   /bin/alertmanager --config.file=/etc/alertmanager/alertmanager.yml"]
