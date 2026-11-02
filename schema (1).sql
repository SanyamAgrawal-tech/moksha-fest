-- MOKSHA (NSUT Cultural Fest) : ER-based schema (3NF)
-- Entities : COLLEGE, PARTICIPANT, EVENT, ENTRY_PASS, VENDOR, STALL, SPONSORSHIP_TIER
-- M:N      : PARTICIPANT <-> EVENT   resolved by REGISTRATION
--            VENDOR <-> STALL        resolved by STALL_BOOKING
--            VENDOR <-> EVENT        resolved by SPONSORSHIP (with TIER)
PRAGMA foreign_keys = ON;

CREATE TABLE COLLEGE (
  college_id INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL UNIQUE,
  city       TEXT,
  is_nsut    INTEGER NOT NULL DEFAULT 0 CHECK (is_nsut IN (0,1))
);

CREATE TABLE PARTICIPANT (
  participant_id INTEGER PRIMARY KEY AUTOINCREMENT,
  full_name      TEXT NOT NULL,
  email          TEXT NOT NULL UNIQUE,
  phone          TEXT NOT NULL,
  age            INTEGER NOT NULL CHECK (age BETWEEN 10 AND 80),
  gender         TEXT NOT NULL CHECK (gender IN ('Male','Female','Other')),
  college_id     INTEGER NOT NULL,
  enrollment_no  TEXT,                -- only for students
  year_of_study  INTEGER,
  course_branch  TEXT,
  state          TEXT,
  emergency_name TEXT NOT NULL,
  emergency_phone TEXT NOT NULL,
  dietary_pref   TEXT CHECK (dietary_pref IN ('Veg','Non-Veg','Jain','Vegan')),
  tshirt_size    TEXT CHECK (tshirt_size IN ('XS','S','M','L','XL','XXL')),
  accommodation  TEXT DEFAULT 'No' CHECK (accommodation IN ('Yes','No')),
  id_proof_type  TEXT,                -- College ID / Aadhaar / Driving Licence ...
  how_heard      TEXT,
  participant_role TEXT,              -- Performer / Audience / Volunteer
  special_needs  TEXT,
  created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (college_id) REFERENCES COLLEGE(college_id)
);

CREATE TABLE EVENT (
  event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
  name       TEXT NOT NULL,
  category   TEXT NOT NULL,           -- Dance / Music / Drama / Art / Fashion
  venue      TEXT NOT NULL,
  event_date TEXT NOT NULL,
  fee        REAL NOT NULL DEFAULT 0,
  max_seats  INTEGER NOT NULL
);

CREATE TABLE REGISTRATION (            -- PARTICIPANT M:N EVENT
  reg_id         INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_id INTEGER NOT NULL,
  event_id       INTEGER NOT NULL,
  reg_date       TEXT DEFAULT CURRENT_TIMESTAMP,
  team_name      TEXT,
  team_size      INTEGER CHECK (team_size BETWEEN 1 AND 30),
  experience_level TEXT,              -- Beginner / Intermediate / Professional
  UNIQUE (participant_id, event_id),
  FOREIGN KEY (participant_id) REFERENCES PARTICIPANT(participant_id) ON DELETE CASCADE,
  FOREIGN KEY (event_id)       REFERENCES EVENT(event_id)             ON DELETE CASCADE
);

CREATE TABLE ENTRY_PASS (              -- 1:N PARTICIPANT -> PASS
  pass_id        INTEGER PRIMARY KEY AUTOINCREMENT,
  participant_id INTEGER NOT NULL,
  pass_type      TEXT NOT NULL CHECK (pass_type IN ('Day 1','Day 2','Day 3','All Days')),
  price          REAL NOT NULL,
  issued_at      TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (participant_id) REFERENCES PARTICIPANT(participant_id) ON DELETE CASCADE
);

CREATE TABLE VENDOR (
  vendor_id      INTEGER PRIMARY KEY AUTOINCREMENT,
  company_name   TEXT NOT NULL,
  contact_person TEXT NOT NULL,
  email          TEXT NOT NULL UNIQUE,
  phone          TEXT NOT NULL,
  business_type  TEXT NOT NULL,       -- Food / Merch / Games / Brand / Other
  website        TEXT,
  social_handle  TEXT,
  address        TEXT,
  city           TEXT,
  gst_number     TEXT,
  fssai_no       TEXT,
  years_in_business INTEGER,
  alt_phone      TEXT,
  created_at     TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE STALL (
  stall_id INTEGER PRIMARY KEY AUTOINCREMENT,
  location TEXT NOT NULL,
  size     TEXT NOT NULL,             -- Small / Medium / Large
  price    REAL NOT NULL,
  status   TEXT NOT NULL DEFAULT 'Available' CHECK (status IN ('Available','Booked'))
);

CREATE TABLE STALL_BOOKING (           -- VENDOR M:N STALL
  booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id  INTEGER NOT NULL,
  stall_id   INTEGER NOT NULL UNIQUE,
  booked_at  TEXT DEFAULT CURRENT_TIMESTAMP,
  products_description TEXT,
  staff_count INTEGER,
  power_required_kw REAL,
  equipment_needed TEXT,
  preferred_days TEXT,
  status     TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending','Approved','Rejected')),
  FOREIGN KEY (vendor_id) REFERENCES VENDOR(vendor_id) ON DELETE CASCADE,
  FOREIGN KEY (stall_id)  REFERENCES STALL(stall_id)
);

CREATE TABLE SPONSORSHIP_TIER (
  tier_id  INTEGER PRIMARY KEY AUTOINCREMENT,
  name     TEXT NOT NULL UNIQUE,      -- Title / Platinum / Gold / Silver
  amount   REAL NOT NULL,
  benefits TEXT
);

CREATE TABLE SPONSORSHIP (             -- VENDOR M:N EVENT (via TIER)
  sponsorship_id INTEGER PRIMARY KEY AUTOINCREMENT,
  vendor_id      INTEGER NOT NULL,
  tier_id        INTEGER NOT NULL,
  event_id       INTEGER,             -- NULL = sponsors the whole fest
  sponsor_type   TEXT,                -- Cash / In-kind / Both
  proposed_amount REAL,
  brand_objective TEXT,
  promo_requirements TEXT,
  status         TEXT NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending','Approved','Rejected')),
  created_at     TEXT DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (vendor_id) REFERENCES VENDOR(vendor_id) ON DELETE CASCADE,
  FOREIGN KEY (tier_id)   REFERENCES SPONSORSHIP_TIER(tier_id),
  FOREIGN KEY (event_id)  REFERENCES EVENT(event_id)
);

-- Keep STALL.status in sync with bookings
CREATE TRIGGER trg_stall_booked AFTER INSERT ON STALL_BOOKING
BEGIN UPDATE STALL SET status='Booked' WHERE stall_id = NEW.stall_id; END;

-- ---------- seed data ----------
INSERT INTO COLLEGE(name,city,is_nsut) VALUES ('NSUT','Delhi',1);
INSERT INTO EVENT(name,category,venue,event_date,fee,max_seats) VALUES
 ('Nritya - Group Dance','Dance','Main Stage','2026-10-29',300,40),
 ('Sur Sangam - Singing','Music','Auditorium','2026-10-29',200,60),
 ('Nukkad Natak','Drama','Open Lawn','2026-10-30',150,30),
 ('Rang Manch - Face Art','Art','Art Block','2026-10-30',100,50),
 ('Ramp Walk','Fashion','Main Stage','2026-10-31',400,25);
INSERT INTO STALL(location,size,price) VALUES
 ('Food Court A1','Medium',8000),('Food Court A2','Medium',8000),
 ('Central Lawn B1','Large',15000),('Central Lawn B2','Large',15000),
 ('Gate 2 C1','Small',4000),('Gate 2 C2','Small',4000);
INSERT INTO SPONSORSHIP_TIER(name,amount,benefits) VALUES
 ('Title Sponsor',500000,'Naming rights, main stage branding, prime stall'),
 ('Platinum',250000,'Stage banners, social media, free stall'),
 ('Gold',100000,'Banners, event-level branding'),
 ('Silver',50000,'Logo on website and posters');
