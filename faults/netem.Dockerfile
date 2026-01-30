FROM alpine:latest

RUN apk add --no-cache bash iproute2

WORKDIR /faults

COPY apply_netem.sh /usr/local/bin/apply_netem.sh
RUN chmod +x /usr/local/bin/apply_netem.sh

CMD ["/usr/local/bin/apply_netem.sh"]

