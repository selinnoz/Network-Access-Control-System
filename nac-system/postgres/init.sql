-- ================================================
-- NAC Sistemi - PostgreSQL Veritabanı Şeması
-- ================================================

CREATE TABLE IF NOT EXISTS radcheck (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(64) NOT NULL,
    attribute   VARCHAR(64) NOT NULL,
    op          VARCHAR(2)  NOT NULL DEFAULT '==',
    value       VARCHAR(253) NOT NULL,
    created_at  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS radreply (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(64) NOT NULL,
    attribute   VARCHAR(64) NOT NULL,
    op          VARCHAR(2)  NOT NULL DEFAULT '=',
    value       VARCHAR(253) NOT NULL
);

CREATE TABLE IF NOT EXISTS radusergroup (
    id          SERIAL PRIMARY KEY,
    username    VARCHAR(64) NOT NULL,
    groupname   VARCHAR(64) NOT NULL,
    priority    INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS radgroupreply (
    id          SERIAL PRIMARY KEY,
    groupname   VARCHAR(64) NOT NULL,
    attribute   VARCHAR(64) NOT NULL,
    op          VARCHAR(2)  NOT NULL DEFAULT '=',
    value       VARCHAR(253) NOT NULL
);

CREATE TABLE IF NOT EXISTS radacct (
    radacctid           BIGSERIAL PRIMARY KEY,
    acctuniqueid        VARCHAR(32) UNIQUE NOT NULL,
    username            VARCHAR(64) NOT NULL,
    nasipaddress        INET NOT NULL,
    nasportid           VARCHAR(15),
    acctstarttime       TIMESTAMP,
    acctstoptime        TIMESTAMP,
    acctsessiontime     INTEGER DEFAULT 0,
    acctinputoctets     BIGINT DEFAULT 0,
    acctoutputoctets    BIGINT DEFAULT 0,
    acctterminatecause  VARCHAR(32),
    callingstationid    VARCHAR(50),
    framedipaddress     INET,
    acctstatustype      VARCHAR(32),
    updated_at          TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS radmac (
    id          SERIAL PRIMARY KEY,
    macaddress  VARCHAR(17) UNIQUE NOT NULL,
    description VARCHAR(128),
    groupname   VARCHAR(64) NOT NULL DEFAULT 'guest',
    active      BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- İndeksler
CREATE INDEX IF NOT EXISTS idx_radcheck_username     ON radcheck(username);
CREATE INDEX IF NOT EXISTS idx_radreply_username     ON radreply(username);
CREATE INDEX IF NOT EXISTS idx_radusergroup_username ON radusergroup(username);
CREATE INDEX IF NOT EXISTS idx_radgroupreply_group   ON radgroupreply(groupname);
CREATE INDEX IF NOT EXISTS idx_radacct_username      ON radacct(username);
CREATE INDEX IF NOT EXISTS idx_radacct_starttime     ON radacct(acctstarttime);
CREATE INDEX IF NOT EXISTS idx_radmac_mac            ON radmac(macaddress);

-- Grup VLAN atamaları (VLAN 10=admin  20=employee  30=guest)
INSERT INTO radgroupreply (groupname, attribute, op, value) VALUES
    ('admin',    'Tunnel-Type',             ':=', '13'),
    ('admin',    'Tunnel-Medium-Type',      ':=', '6'),
    ('admin',    'Tunnel-Private-Group-Id', ':=', '10'),
    ('employee', 'Tunnel-Type',             ':=', '13'),
    ('employee', 'Tunnel-Medium-Type',      ':=', '6'),
    ('employee', 'Tunnel-Private-Group-Id', ':=', '20'),
    ('guest',    'Tunnel-Type',             ':=', '13'),
    ('guest',    'Tunnel-Medium-Type',      ':=', '6'),
    ('guest',    'Tunnel-Private-Group-Id', ':=', '30');

-- Test kullanıcıları (alice: admin123 | bob: employee123 | guest: guest123)
INSERT INTO radcheck (username, attribute, op, value) VALUES
    ('alice', 'Crypt-Password', ':=', '$2b$12$Zq27WjCP3n14wXxkINbAZu9fOb.BQHmxaBni1iXnHx9XbHA3O2AOS'),
    ('bob',   'Crypt-Password', ':=', '$2b$12$PzXzAcYjm1D91hbzQUhuHO7NQWrizQQ9XzsHfFnQmjvubyhd0GFVC'),
    ('guest', 'Crypt-Password', ':=', '$2b$12$3QikjLlZb45G3xCsYj9NHeCP6jSnIFCrR.9KEJ.ny2dx.5UyebR.G');

INSERT INTO radusergroup (username, groupname, priority) VALUES
    ('alice', 'admin',    1),
    ('bob',   'employee', 1),
    ('guest', 'guest',    1);

-- Test MAC adresleri (MAB için)
INSERT INTO radmac (macaddress, description, groupname) VALUES
    ('aa:bb:cc:dd:ee:ff', 'Test yazici',   'employee'),
    ('11:22:33:44:55:66', 'IP telefon',    'employee'),
    ('de:ad:be:ef:00:01', 'Misafir cihaz', 'guest');