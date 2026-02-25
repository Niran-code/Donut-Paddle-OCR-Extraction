import re
from typing import Dict, Any

class RegexCleaner:
    def parse_aadhaar(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {
            "document_type": "Aadhaar Card",
        }
        aadhaar_match = re.search(r"\b(\d{4}\s?\d{4}\s?\d{4})\b", text)
        if aadhaar_match:
            raw_num = aadhaar_match.group(1).replace(" ", "")
            data["aadhaar_number"] = f"{raw_num[:4]} {raw_num[4:8]} {raw_num[8:]}"
            
        dob_match = re.search(r"\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b", text)
        if dob_match:
            data["dob"] = dob_match.group(1).replace("/", "-")
            
        if "dob" not in data:
             yob_match = re.search(r"Year of Birth\s*[:\-]?\s*(\d{4})", text, re.IGNORECASE)
             if yob_match:
                 data["dob"] = f"{yob_match.group(1)}-01-01"
        
        if re.search(r"\b(Male|MALE)\b", text):
            data["gender"] = "Male"
        elif re.search(r"\b(Female|FEMALE)\b", text):
            data["gender"] = "Female"
            
        lines = [line.strip() for line in full_text_lines if line.strip()]
        for line in lines:
             if any(x in line.lower() for x in ["govt", "india", "unique", "authorit", "enrollment", "help", "www", "dob", "year", "male", "female"]):
                 continue
             if re.match(r"^[A-Z][a-z]+(\s[A-Z][a-z]+)+$", line) or re.match(r"^[A-Z\s]+$", line):
                 if len(line.split()) < 2: continue
                 data["name"] = line.title()
                 break
        return data

    def parse_pan(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {
            "document_type": "PAN Card",
        }
        pan_pattern = re.compile(r"[A-Z]{5}[0-9]{4}[A-Z]")
        pan_match = pan_pattern.search(text)
        if pan_match:
            data["pan_number"] = pan_match.group(0)

        dob_pattern = re.compile(r"\b(\d{2}[/-]\d{2}[/-]\d{4})\b")
        dob_match = dob_pattern.search(text)
        if dob_match:
            data["dob"] = dob_match.group(1).replace('/', '-')
        
        lines = [line.strip() for line in full_text_lines if line.strip()]
        found_name = False
        found_fname = False
        
        for i, line in enumerate(lines):
            if "Father" in line or "Mother" in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1]
                    if not any(x in candidate for x in ["Number", "Card", "Signature", "Date", "DOB"]):
                         data["father_name"] = candidate
                         found_fname = True
                continue
            
            if "Name" in line and "Father" not in line and "Mother" not in line:
                if i + 1 < len(lines):
                    candidate = lines[i+1]
                    if not any(x in candidate for x in ["Number", "Card", "Father", "Mother"]):
                        data["name"] = candidate
                        found_name = True

        # Positional heuristic (modern cards: Name is ~2 lines above DOB, Father Name is ~1 line above DOB)
        if "dob" in data and (not found_name or not found_fname):
            dob_str = data["dob"].replace('-', '/')
            dob_index = -1
            for i, line in enumerate(lines):
                if dob_str in line or data["dob"] in line or re.search(r"\b\d{2}[/-]\d{2}[/-]\d{4}\b", line):
                    dob_index = i
                    break
                    
            if dob_index >= 2:
                # Iterate backwards to skip blank lines or weird artifacts
                fname_candidate = ""
                name_candidate = ""
                
                # Father Name usually directly above DOB
                if not found_fname:
                    fname_candidate = lines[dob_index - 1]
                    if not any(x in fname_candidate.upper() for x in ["GOVT", "TAX", "DEPARTMENT", "INDIA", "INCOME"]):
                        data["father_name"] = fname_candidate
                
                # Name usually directly above Father
                if not found_name:
                    name_candidate = lines[dob_index - 2]
                    if not any(x in name_candidate.upper() for x in ["GOVT", "TAX", "DEPARTMENT", "INDIA", "INCOME"]):
                        data["name"] = name_candidate

        return data
        
    def extract_marksheet_details(self, text: str, lines: list) -> Dict[str, Any]:
        # Copied verbatim from previous extractor to prevent regressions
        data = {
            "document_type": "Marksheet",
            "university_name": "Unknown",
            "college_name": "Unknown",
            "student_name": "Unknown",
            "university_seat_number": "Unknown",
            "semester": "Unknown",
            "subjects": [],
            "semester_2": [], 
            "semester_1": [], 
            "remarks": {"P": "Pass", "F": "Fail", "A": "Absent", "W": "Withheld", "X": "Not Eligible"}
        }
        uni_match = re.search(r"(Visvesvaraya\s+Technological\s+University|VTU|Anna\s+University)", text, re.IGNORECASE)
        if uni_match:
            data["university_name"] = uni_match.group(1).title()
            
        usn_match = re.search(r"\b([1-4][A-Z]{2}\d{2}[A-Z]{2,6}\d{1,3})\b", text)
        if usn_match:
            data["university_seat_number"] = usn_match.group(1).upper()
            
        for i, line in enumerate(lines):
            if "Name" in line and ":" in line:
                parts = line.split(":")
                if len(parts) > 1:
                    clean_name = parts[1].strip()
                    if clean_name and not any(x in clean_name.lower() for x in ["usn", "semester", "result"]):
                        data["student_name"] = clean_name.title()
                        break
            elif "Name" in line or "NAME" in line:
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    if next_line.startswith(":"):
                        clean_name = next_line.replace(":", "").strip()
                        if clean_name and not any(x in clean_name.lower() for x in ["usn", "semester", "result"]):
                            data["student_name"] = clean_name.title()
                            break

        all_semesters_map = {"1": [], "2": [], "3": [], "4": [], "5": [], "6": [], "7": [], "8": []}
        latest_sem = 0
        current_semester = None
        state = 'LOOKING_FOR_CODE'
        current_subject = {}
        name_buffer = []
        marks_buffer = []
        
        sem_header_pattern = re.compile(r"Semester\s*[:\-]?\s*(\d+)", re.IGNORECASE)
        code_pattern = re.compile(r"^[A-Z0-9]{5,8}$")
        
        for line in lines:
            clean_line = line.strip()
            if not clean_line: continue
            
            sem_match = sem_header_pattern.search(clean_line)
            if sem_match:
                sem_val = sem_match.group(1)
                current_semester = sem_val
                if int(sem_val) > latest_sem:
                    latest_sem = int(sem_val)
                state = 'LOOKING_FOR_CODE'
                current_subject = {}
                name_buffer = []
                marks_buffer = []
                continue

            # Check if this is a NEW SUBJECT CODE
            is_new_code = False
            if "Code" not in clean_line and "Subject" not in clean_line:
                parts = clean_line.split()
                if len(parts) == 1 and (re.match(r"^\d{2}[A-Z]{2,3}\d{2,4}$", parts[0]) or re.match(r"^[A-Z]{2,3}\d{2,4}$", parts[0])):
                    is_new_code = True

            if is_new_code:
                # Force push previous subject if it was stuck (e.g. OCR misread the 'Pass/Fail' column)
                if current_subject and 'subject_code' in current_subject and 'result' not in current_subject:
                    if len(marks_buffer) >= 3:
                        current_subject['internal_marks'] = marks_buffer[-3]
                        current_subject['external_marks'] = marks_buffer[-2]
                        current_subject['total'] = marks_buffer[-1]
                        current_subject['result'] = "Unknown"
                        if current_semester: all_semesters_map.get(current_semester, []).append(current_subject)

                current_subject = {}
                current_subject['subject_code'] = parts[0]
                state = 'BUILDING_NAME'
                name_buffer = []
                marks_buffer = []
                continue

            if state == 'LOOKING_FOR_CODE':
                # If we have a completed subject, append orphan text to its name to fix alignment splits
                if current_subject and 'result' in current_subject:
                    if re.match(r"\d{4}-\d{2}-\d{2}", clean_line) or clean_line.upper() in ["OF", "NA", "N/A"]: continue
                    if clean_line.lower() in ["internal", "external", "total", "result", "grade", "marks", "announced", "/updated", "on", "fail", "pass", "p", "f", "a", "w", "x", "ne->"]: continue
                    if "Nomenclature" in clean_line or "->" in clean_line or "ELIGIBLE" in clean_line.upper(): continue
                    
                    name_buffer.append(clean_line)
                    current_subject['subject_name'] = " ".join(name_buffer).strip()

            elif state == 'BUILDING_NAME':
                if clean_line.isdigit():
                    marks_buffer = [clean_line]
                    current_subject['subject_name'] = " ".join(name_buffer).strip()
                    state = 'LOOKING_FOR_MARKS'
                elif re.match(r"^\d+$", clean_line):
                     marks_buffer = [clean_line]
                     current_subject['subject_name'] = " ".join(name_buffer).strip()
                     state = 'LOOKING_FOR_MARKS'
                else:
                    if clean_line.lower() in ["internal", "external", "total", "result", "grade"]: continue
                    name_buffer.append(clean_line)
            
            elif state == 'LOOKING_FOR_MARKS':
                if clean_line.isdigit():
                    marks_buffer.append(clean_line)
                elif clean_line.upper() in ["A", "X", "-"]:
                     marks_buffer.append("0" if clean_line == "-" else clean_line)
                elif re.match(r"^[PFAWX]$", clean_line.upper()) or clean_line.upper() in ["PASS", "FAIL", "OF", "0F", "NA"]:
                     state = 'LOOKING_FOR_RESULT'
                     res = clean_line.upper()
                     if res in ["PASS", "FAIL"]: res = res[0]
                     if res in ["OF", "0F"]: res = "F"
                     
                     if len(marks_buffer) >= 3:
                        current_subject['internal_marks'] = marks_buffer[-3]
                        current_subject['external_marks'] = marks_buffer[-2]
                        current_subject['total'] = marks_buffer[-1]
                        current_subject['result'] = res
                        if current_semester: all_semesters_map.get(current_semester, []).append(current_subject)
                        state = 'LOOKING_FOR_CODE'
                        marks_buffer = []

            elif state == 'LOOKING_FOR_RESULT':
                res = clean_line.upper()
                if res in ["P", "F", "A", "W", "X", "PASS", "FAIL", "OF", "0F", "NA"]:
                    if res in ["PASS", "FAIL"]: res = res[0]
                    if res in ["OF", "0F"]: res = "F"
                    if len(marks_buffer) >= 3:
                        current_subject['internal_marks'] = marks_buffer[-3]
                        current_subject['external_marks'] = marks_buffer[-2]
                        current_subject['total'] = marks_buffer[-1]
                        current_subject['result'] = res
                        if current_semester: all_semesters_map.get(current_semester, []).append(current_subject)
                    state = 'LOOKING_FOR_CODE'
                    marks_buffer = []

        data["semester"] = str(latest_sem) if latest_sem > 0 else "Unknown"
        if latest_sem > 0:
            data["subjects"] = all_semesters_map.get(str(latest_sem), [])
            if int(latest_sem) > 1:
                sem_2 = all_semesters_map.get("2", [])
                if sem_2: data["semester_2"] = sem_2
                sem_1 = all_semesters_map.get("1", [])
                if sem_1: data["semester_1"] = sem_1
        return data

    def parse_dl(self, text: str, full_text_lines: list) -> Dict[str, Any]:
        data = {
            "document_type": "driving_license",
            "vehicle_classes": [],
            "address": {}
        }
        
        lines = [line.strip() for line in full_text_lines if line.strip()]
        
        for i, line in enumerate(lines):
            # Form Number
            if "FORM" in line.upper():
                form_match = re.search(r"FORM\s*-\s*\d+", line, re.IGNORECASE)
                if form_match: data["form_number"] = form_match.group(0).upper()
            
            # DL Number
            if "DL No" in line or "DLNo" in line or line.startswith("DL"):
                if ":" in line and len(line.split(":")) > 1:
                    data["dl_number"] = line.split(":")[1].strip()
                elif i + 1 < len(lines):
                    data["dl_number"] = lines[i+1].replace(":", "").strip()
                    
            # Issue Date
            if "DOI" in line.upper() and not "CDOI" in line.upper():
                doi_match = re.search(r"\d{2}-\d{2}-\d{4}", line)
                if doi_match: data["date_of_issue"] = doi_match.group(0)

            # Name
            if line.upper() == "NAME":
                if i + 1 < len(lines):
                    data["name"] = lines[i+1].replace(":", "").strip()
                    
            # DOB
            if "D.O.B" in line.upper() or "DOB" in line.upper():
                if i + 1 < len(lines) and re.match(r"\d{2}-\d{2}-\d{4}", lines[i+1]):
                    data["date_of_birth"] = lines[i+1]
                else:
                    dob_match = re.search(r"\d{2}-\d{2}-\d{4}", line)
                    if dob_match: data["date_of_birth"] = dob_match.group(0)

            # Valid Till
            if "VALIDTILL" in line.upper() or "VALID TILL" in line.upper():
                val_match = re.search(r"\d{2}-\d{2}-\d{4}", line)
                if val_match: data["valid_till"] = val_match.group(0)
                
            # National Validity
            if "THROUGHOUT INDIA" in line.upper():
                data["national_validity"] = line.strip()

            # Father Name
            if line.upper() == "S/O" or line.upper() == "SLO" or line.upper() == "D/O" or line.upper() == "W/O" or "S/O" in line.upper() or "SLO" in line.upper():
                 if ":" in line and len(line.split(":")) > 1:
                     data["father_name"] = line.split(":")[1].strip()
                 elif i + 1 < len(lines):
                     data["father_name"] = lines[i+1].replace(":", "").strip()
                     
            # Vehicle Classes (MCWG, LMV etc)
            if "MCWG" in line.upper() or "LMV" in line.upper() or "HMV" in line.upper() or "MCWOG" in line.upper():
                 vclass = ""
                 if "MCWG" in line.upper(): vclass = "MCWG"
                 elif "LMV" in line.upper(): vclass = "LMV"
                 elif "HMV" in line.upper(): vclass = "HMV"
                 elif "MCWOG" in line.upper(): vclass = "MCWOG"
                 
                 issue_dt = ""
                 if i + 1 < len(lines) and re.match(r"\d{2}-\d{2}-\d{4}", lines[i+1]):
                     issue_dt = lines[i+1]
                 elif i - 1 >= 0 and re.match(r"\d{2}-\d{2}-\d{4}", lines[i-1]):
                     issue_dt = lines[i-1]
                 elif "DOI" in line.upper():
                     dt_match = re.search(r"\d{2}-\d{2}-\d{4}", line)
                     if dt_match: issue_dt = dt_match.group(0)
                 elif dt_local := re.search(r"\d{2}-\d{2}-\d{4}", line):
                     issue_dt = dt_local.group(0)
                 
                 if vclass and not any(vc.get('class') == vclass for vc in data["vehicle_classes"]):
                     data["vehicle_classes"].append({
                         "class": vclass,
                         "issue_date": issue_dt
                     })
                 
            # Address parsing logic (Starts at "ADDRESS" and ends at "Sign." or "Pin")
            if "ADDRESS" in line.upper():
                full_address = ""
                if ":" in line:
                    full_address += line.split(":")[1].strip() + " "
                
                for j in range(i+1, min(i+5, len(lines))):
                    addr_line = lines[j]
                    if "Sign" in addr_line or "Authority" in addr_line or "RTO" in addr_line:
                        break
                    full_address += addr_line + " "
                    
                full_address = full_address.strip()
                
                # Attempt to structure if it contains commas or specific formatting
                if full_address:
                    data["address"]["full_raw_address"] = full_address
                    parts = [p.strip() for p in re.split(r'[,|]', full_address) if p.strip()]
                    
                    if len(parts) > 0:
                        # Street is usually the first chunk
                        # Area might be mixed with Street
                        # Try to find 'TOWN', 'STREET', etc to split Area from Street if no comma
                        street_val = parts[0]
                        
                        street_parts = [s.strip() for s in re.split(r'(?i)(TOWN\b)', street_val) if s.strip()]
                        
                        if len(street_parts) > 1:
                            data["address"]["street"] = street_parts[0].replace("TOWN", "").strip()
                            data["address"]["area"] = (street_parts[0].split()[-1] if len(street_parts[0].split()) > 0 else "") + " TOWN"
                        elif "STREET" in street_val.upper() and len(street_val) > 20:
                           # "CHURCH ROAD MARATA STREET ANEKAL TOwN Anekal" -> Street up to STREET, Area after
                           idx = street_val.upper().find("STREET") + 6
                           data["address"]["street"] = street_val[:idx].strip()
                           data["address"]["area"] = street_val[idx:].strip()
                           
                           # further split area and city if mixed
                           area_parts = data["address"]["area"].split(" ")
                           if len(area_parts) > 2 and area_parts[-1].upper() == area_parts[-2].upper():
                               data["address"]["city"] = area_parts[-1].title()
                               data["address"]["area"] = " ".join(area_parts[:-1]).strip()
                           elif len(area_parts) > 0:
                               data["address"]["city"] = area_parts[-1].title()
                               
                        else:
                            data["address"]["street"] = street_val

                    if len(parts) > 1:
                        # Next part is usually City/District and State
                        dist_state = parts[1].split()
                        if len(dist_state) > 0:
                            data["address"]["district"] = dist_state[0]
                        if len(dist_state) > 1:
                            data["address"]["state"] = dist_state[1]

                    # Extract pincode anywhere
                    pin_match = re.search(r"\b\d{6}\b", full_address)
                    if pin_match:
                         data["address"]["postal_code"] = pin_match.group(0)
                
            # Issuing Authority (usually at the bottom with RTO)
            if "RTO" in line.upper():
                 data["issuing_authority"] = line.strip()

        return data

    def extract_document(self, raw_text: str, lines: list) -> Dict[str, Any]:
        """Tries to parse document parameters from arbitrary text. Returns dict of keys."""
        base_data = {}
        # Aadhaar detection: Look for 12 digits (with or without spaces), or MALE/FEMALE keywords
        if re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", raw_text) or "MALE" in raw_text.upper() or "FEMALE" in raw_text.upper() or "DOB" in raw_text.upper():
             base_data = self.parse_aadhaar(raw_text, lines)
        
        if not base_data.get("document_type") and re.search(r"[A-Z]{5}\d{4}[A-Z]", raw_text):
             base_data = self.parse_pan(raw_text, lines)
             
        if not base_data.get("document_type") and ( "UNIVERSITY" in raw_text.upper() or "MARKS" in raw_text.upper() or "RESULT" in raw_text.upper()):
             base_data = self.extract_marksheet_details(raw_text, lines)
             
        if not base_data.get("document_type") and ( "DL No" in raw_text or "DLNo" in raw_text or "DRIVING LICENCE" in raw_text.upper() or "THROUGHOUT INDIA" in raw_text.upper() or "LICENCING AUTHORITY" in raw_text.upper()):
             base_data = self.parse_dl(raw_text, lines)
        
        # Simple extraction for DL/Passport/VoterID logic would go here, falling back to Donut usually
        if not base_data.get("document_type"):
            base_data["document_type"] = "Unknown"
            
        return base_data
