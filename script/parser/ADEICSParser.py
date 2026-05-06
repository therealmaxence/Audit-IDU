import pandas as pd
from icalendar import Calendar
from .Parser import Parser
 
 
class ADEICSParser(Parser):
    def __init__(self):
        super().__init__(supported_extensions=[".ics"])
    
    def __preprocess__(self, f):
        """Lit le contenu du fichier JSON et le convertit en une liste de dictionnaires."""
        return Calendar.from_ical(f.read())
    
    def __parse__(self, raw):
        events = []
        for component in raw.walk():
            if component.name == "VEVENT":
                event_data = {
                                "Title": str(component.get("SUMMARY", "")),
                                "Location": str(component.get("LOCATION", "")),
                                "Starts": component.get("DTSTART", "").dt,
                                "Ends": component.get("DTEND", "").dt,
                                "Description": str(component.get("DESCRIPTION", ""))
                            }
                events.append(event_data)
        df = pd.DataFrame(events)
        for col in ("Starts", "Ends"):
            df[col] = pd.to_datetime(df[col], utc=True, errors="coerce")
        return df