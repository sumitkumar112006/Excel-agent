import sys, os, glob, re
sys.stdout.reconfigure(encoding='utf-8')
import pymupdf
from unidecode import unidecode

pdf_files = glob.glob('01-Oct-25 To 31-Dec-25/*.pdf')

def extract_org_name_clean(text):
    text = text.replace('\ufb00', 'ff').replace('\ufb01', 'fi').replace('\ufb02', 'fl').replace('\ufb03', 'ffi').replace('\ufb04', 'ffl')
    
    # 1. Extract Organisation Details section
    m_sec = re.search(r'(?:Organisation\s*Details|संगठन[^\n:]*विवरण|संगठन[^\n:]*ववरण|संगठन)[\s\S]+?(?=Buyer\s*Details|खरीदार|Financial\s*Approval|Paying\s*Authority|Seller\s*Details|$)', text, re.I)
    section = m_sec.group(0) if m_sec else text[:2000]
    
    # 2. Extract strictly Organisation Name
    label_pattern = re.compile(
        r'(?:संगठन\s*का\s*(?:\n\s*)?नाम\s*(?:[|/\\–\-]\s*)?Organisation\s*Name|Organisation\s*Name\s*(?:[|/\\–\-]\s*)?संगठन\s*का\s*(?:\n\s*)?नाम|Organisation\s*Name|संगठन\s*का\s*नाम|संगठन\s*नाम|sNgtthn\s*kaa\s*naam)\s*[:.\-–=]*\s*',
        re.I
    )
    
    m = label_pattern.search(section)
    if not m:
        return 'NA'
    
    # Scan subsequent lines until next heading
    remaining = section[m.end():].lstrip('\r\n')
    lines = remaining.split('\n')
    
    # Stop headings: Must match as a HEADING (with colon or at start of line as heading)
    stop_heading_pats = [
        r'^(?:[^\n:]*?(?:काया|कार्यालय|kaayaa|Office\s*Zone|Oﬃce\s*Zone)\b\s*[:|.\-–=])',
        r'^(?:[^\n:]*?(?:Buyer\s*Details|खरीदार|Buying\s*Organisation)\b)',
        r'^(?:[^\n:]*?(?:Department|विभाग|वभाग)\b\s*[:|.\-–=])',
        r'^(?:[^\n:]*?(?:Ministry|मंत्रालय)\b\s*[:|.\-–=])',
        r'^(?:[^\n:]*?(?:Type|प्रारूप)\b\s*[:|.\-–=])',
        r'^(?:[^\n:]*?(?:Paying\s*Authority|भुगतान)\b)',
        r'^(?:[^\n:]*?(?:Financial\s*Approval|वित्तीय)\b)',
    ]
    
    val_parts = []
    for line in lines[:5]:
        line_s = line.strip()
        if not line_s:
            if val_parts:
                break
            continue
        
        # Check if line matches any stop heading pattern
        is_stop = False
        for pat in stop_heading_pats:
            if re.search(pat, line_s, re.I):
                is_stop = True
                break
        if is_stop:
            break
            
        # If line contains inline next heading e.g. "Adg Pac कायाEलय Fे=|Oﬃce Zone: ..."
        m_inline_stop = re.search(r'\s+(?:काया[^\n:]*|कार्यालय[^\n:]*|Office\s*Zone|Oﬃce\s*Zone|Buyer\s*Details|खरीदार)\s*[:|.\-–=]', line_s, re.I)
        if m_inline_stop:
            val_parts.append(line_s[:m_inline_stop.start()].strip())
            break
            
        val_parts.append(line_s)
    
    if not val_parts:
        return 'NA'
    
    val = ' '.join(val_parts).strip()
    
    # Strip any trailing label artifacts
    val = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', val)
    val = re.sub(r'\s+', ' ', val).strip()
    val = re.sub(r'^[:|\-–\s]+|[:|\-–\s]+$', '', val).strip()
    
    if unidecode(val) != val:
        val = unidecode(val)
        
    if not val or val.upper() in {'-', '--', 'N/A', 'NONE', 'NULL', 'NA', 'N / A', 'ORGANISATION', 'संगठन', 'ORGANISATION NAME'}:
        return 'NA'
        
    return val

print(f'Testing Organisation Name extraction across {len(pdf_files)} PDFs...')
org_counts = {'NA': 0, 'VALID': 0}
sample_orgs = []
for p in pdf_files:
    doc = pymupdf.open(p)
    text = doc[0].get_text('text')
    doc.close()
    
    org_res = extract_org_name_clean(text)
    if org_res == 'NA':
        org_counts['NA'] += 1
    else:
        org_counts['VALID'] += 1
    sample_orgs.append((os.path.basename(p), org_res))

print(f"Total: {len(pdf_files)}, Valid Org Names: {org_counts['VALID']}, Explicit NA: {org_counts['NA']}")
print('\nSample 35 extractions:')
for f, o in sample_orgs[:35]:
    print(f'{f:45} -> {o}')
