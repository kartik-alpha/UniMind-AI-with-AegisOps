import sys
from pathlib import Path

def create_sample_pdf(output_path: str):
    """
    Generates a valid, readable institutional PDF document for UniMind AI RAG testing.
    """
    lines = [
        "UniMind University Institutional Academic Regulations and Examination Code 2026",
        "Official Policy Document - Academic Affairs & Registrar Directorate",
        "",
        "Section 1: Mandatory Attendance Policy",
        "1.1 All enrolled undergraduate and postgraduate students must maintain a minimum of 75 percent attendance in every registered course to be eligible for end-semester examinations.",
        "1.2 Medical leaves up to a maximum of 10 percent can be condoned by the Dean of Academic Affairs upon submission of verified hospital documentation within 7 working days of absence.",
        "1.3 Students with attendance below 65 percent are automatically debarred (grade FA) and must repeat the course.",
        "",
        "Section 2: Examination Conduct and Grading Framework",
        "2.1 The grading scale operates on a 10-point Absolute CGPA framework. Minimum passing grade is D (4.0 points).",
        "2.2 Make-up examinations are permitted solely for students with sanctioned medical leaves or approved official university representation in national competitions.",
        "2.3 Possession of unauthorized electronic devices during examinations results in immediate confiscation and disciplinary committee referral under Category C misconduct.",
        "",
        "Section 3: Digital Campus and Lab Access Rules",
        "3.1 High-performance computing labs and AI servers are available 24/7 for enrolled engineering scholars with valid biometric keycard access.",
        "3.2 Unauthorized port scanning, network tampering, or denial of service attempts on university intranet services results in immediate suspension of computing privileges."
    ]

    # Build clean PDF stream content
    stream_content = "BT\n/F1 11 Tf\n50 740 Td\n14 TL\n"
    for line in lines:
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if not line:
            stream_content += "T*\n"
        else:
            stream_content += f"({escaped}) '\n"
    stream_content += "ET\n"
    stream_bytes = stream_content.encode("latin-1", errors="replace")

    pdf_parts = []
    pdf_parts.append(b"%PDF-1.4\n")
    
    offsets = []
    
    # 1 0 obj Catalog
    offsets.append(sum(len(p) for p in pdf_parts))
    pdf_parts.append(b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n")
    
    # 2 0 obj Pages
    offsets.append(sum(len(p) for p in pdf_parts))
    pdf_parts.append(b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n")
    
    # 3 0 obj Page
    offsets.append(sum(len(p) for p in pdf_parts))
    pdf_parts.append(b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n")
    
    # 4 0 obj Font
    offsets.append(sum(len(p) for p in pdf_parts))
    pdf_parts.append(b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n")
    
    # 5 0 obj Stream
    offsets.append(sum(len(p) for p in pdf_parts))
    pdf_parts.append(f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii") + stream_bytes + b"\nendstream\nendobj\n")
    
    xref_offset = sum(len(p) for p in pdf_parts)
    xref = f"xref\n0 {len(offsets)+1}\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"
    pdf_parts.append(xref.encode("ascii"))
    
    trailer = f"trailer\n<< /Size {len(offsets)+1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n"
    pdf_parts.append(trailer.encode("ascii"))

    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "wb") as f:
        for part in pdf_parts:
            f.write(part)
            
    print(f"Generated institutional PDF at: {out_file} ({out_file.stat().st_size} bytes)")
    
    # Verify with pypdf
    import pypdf
    reader = pypdf.PdfReader(str(out_file))
    print(f"Extracted {len(reader.pages)} page(s). First 120 chars:")
    print(repr(reader.pages[0].extract_text()[:120]))

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_institutional_policy.pdf"
    create_sample_pdf(path)
