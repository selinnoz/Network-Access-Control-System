FROM freeradius/freeradius-server:latest-3.2
 
# PostgreSQL sürücüsü için gerekli paketler
RUN apt-get update && apt-get install -y \
    libpq-dev \
    freeradius-postgresql \
    && rm -rf /var/lib/apt/lists/*
 
# Konfigürasyon dosyalarını kopyala
COPY clients.conf       /etc/freeradius/clients.conf
COPY sql.conf           /etc/freeradius/mods-available/sql
COPY sites-enabled/default /etc/freeradius/sites-enabled/default
COPY mods-enabled/rest  /etc/freeradius/mods-enabled/rest
 
# sql modülünü etkinleştir
RUN ln -sf /etc/freeradius/mods-available/sql \
           /etc/freeradius/mods-enabled/sql
 
EXPOSE 1812/udp 1813/udp
 
CMD ["freeradius", "-f"]
 