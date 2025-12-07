# Data Source Merge Logic

## Overview

The code now intelligently merges data from your old data source into the new data source columns.

## Merge Rules (Only fills if target is empty)

### 1. Full Name

```
IF "Full Name" is empty:
    "Full Name" = "Name (First)" + " " + "Name (Last)"
ELSE:
    Keep existing "Full Name" value (from new data source)
```

**Example:**

- Old data: First="Sarah", Last="Massopust", Full Name=""
- Result: Full Name="Sarah Massopust"

- New data: First="", Last="", Full Name="John Doe"
- Result: Full Name="John Doe" (unchanged)

---

### 2. City

```
IF "City" is empty:
    "City" = "City/Town"
ELSE:
    Keep existing "City" value (from new data source)
```

**Example:**

- Old data: City/Town="Kenedy", City=""
- Result: City="Kenedy"

- New data: City/Town="", City="Milwaukee"
- Result: City="Milwaukee" (unchanged)

---

### 3. Primary Subject

```
IF "Primary Subject" is empty:
    "Primary Subject" = "Computed STEM/Tech/Non-STEM"
ELSE:
    Keep existing "Primary Subject" value (from new data source)
```

**Example:**

- Old data: Computed="STEM, Technology", Primary Subject=""
- Result: Primary Subject="STEM, Technology"

- New data: Computed="", Primary Subject="stem"
- Result: Primary Subject="stem" (unchanged)

---

### 4. Ages Taught

```
IF "Ages Taught" is empty:
    "Ages Taught" = "Computed Grade Band"
ELSE:
    Keep existing "Ages Taught" value (from new data source)
```

**Example:**

- Old data: Grade Band="K-2, 3-5", Ages Taught=""
- Result: Ages Taught="K-2, 3-5"

- New data: Grade Band="", Ages Taught="earlyElementary, upperElementary"
- Result: Ages Taught="earlyElementary, upperElementary" (unchanged)

---

## Output CSV Structure

Both old and new columns are preserved:

```
Email Address
Name (First)          ← Old source
Name (Last)           ← Old source
Full Name             ← New source (merged from First + Last if empty)
I am a...
School / Company Name
Country
City/Town             ← Old source
City                  ← New source (merged from City/Town if empty)
State
Zip Code
Computed Grade Band   ← Old source (computed)
Ages Taught           ← New source (merged from Grade Band if empty)
Computed STEM/...     ← Old source (computed)
Primary Subject       ← New source (merged from Computed if empty)
... (all other columns)
```

## Benefits

✅ **Non-destructive:** Never overwrites existing data from new source
✅ **Backward compatible:** Old data still works perfectly
✅ **Forward compatible:** New data source values take precedence
✅ **Seamless integration:** Single CSV with both data sources merged
