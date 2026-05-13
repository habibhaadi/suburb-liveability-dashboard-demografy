# suburb-liveability-dashboard-demografy

Most suburb comparison tools feel like someone dumped census tables into a website and called it a day.

This wasn’t built for that.

The idea started with a pretty simple question:

> *How do you actually compare two suburbs properly without spending hours jumping between Google Maps tabs, rental sites, train lines, café counts and random Reddit threads?*

So instead of manually checking:

* gyms
* parks
* schools
* supermarkets
* transit
* cafés
* travel times
* affordability

…this app turns the whole process into a live comparison engine.

You enter two suburbs.

The pipeline handles the rest.

---

## What this actually is

An interactive suburb comparison dashboard built using:

* Streamlit
* Supabase (PostgreSQL)
* Google Places API
* Google Routes API
* Python
* real-time caching architecture

The app compares Australian suburbs across:

* lifestyle
* social density
* mobility
* outdoor activity
* family infrastructure
* affordability

while trying to keep the experience clean, fast and visually premium.

---

## The fun part

The app doesn’t just spam API calls every time someone searches.

That gets expensive very quickly.

So the system works like this:

```text
User searches suburb
        ↓
Check Supabase cache
        ↓
Already exists?
   ↙          ↘
 Yes           No
  ↓             ↓
Return data   Fetch from Google APIs
                  ↓
          Process + transform
                  ↓
            Save to database
                  ↓
          Return live results
```

Basically:

* fast for users
* cheaper to run
* scalable
* less redundant API usage

---

## Some engineering things I’m genuinely proud of

### Viewport tiling fallback logic

Google Places API can “saturate” results in dense suburbs.

So instead of accepting incomplete data, the app dynamically splits suburbs into smaller geographic tiles and re-queries them to improve coverage.

Not gonna lie — this part nearly cooked me.

---

### Weighted livability scoring

The app converts raw amenity counts into weighted category scores using:

* density normalisation
* population scaling
* travel metrics
* affordability scoring

to create a cleaner suburb profile rather than just throwing raw numbers on screen.

---

### Premium UI direction

Most data projects stop at “functional”.

I wanted this to feel more like a product.

Dark UI.
Glassmorphism.
Soft gradients.
Minimal clutter.
Apple-inspired spacing and hierarchy.

The goal was:

> data-heavy without feeling overwhelming.

---

# Features

* Real-time suburb comparison
* Google Places integration
* CBD travel calculations
* Population & area scaling
* Affordability scoring
* Supabase caching
* Interactive comparison dashboard
* Error handling & validation
* Responsive premium UI

---

# Project Structure

```bash
app/
    app.py

pipeline/
    add_rent.py
    generate_suburb_area.py
    generate_suburb_population.py
    test_reference_data.py

    data/
        suburb_reference.csv
```

---

# Running locally

```bash
streamlit run app/app.py
```

Environment variables required:

```env
SUPABASE_URL=
SUPABASE_SERVICE_KEY=
GOOGLE_API_KEY=
```

---

# Tech Stack

| Layer           | Tools                                |
| --------------- | ------------------------------------ |
| Frontend        | Streamlit                            |
| Database        | Supabase / PostgreSQL                |
| APIs            | Google Places API, Google Routes API |
| Data Processing | Python, Pandas                       |
| Architecture    | Cache-first event-driven pipeline    |

---

# Final thoughts

This started as an internship project brief around suburb livability.

Somewhere along the way it turned into:

* data engineering
* product design
* API architecture
* caching systems
* geospatial querying
* UI/UX experimentation
* and an unhealthy number of late-night debugging sessions.

Worth it though.

---

Built by Habib Haadi
