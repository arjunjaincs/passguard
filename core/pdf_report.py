"""
PDF report generator for PassGuard security audits.
Creates professional PDF reports with watermark and formatting.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from datetime import datetime
import os


class WatermarkCanvas(canvas.Canvas):
    """Custom canvas with PassGuard watermark."""
    
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self.pages = []
    
    def showPage(self):
        self.pages.append(dict(self.__dict__))
        self._startPage()
    
    def save(self):
        page_count = len(self.pages)
        for i, page in enumerate(self.pages):
            self.__dict__.update(page)
            self.draw_watermark(i + 1, page_count)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)
    
    def draw_watermark(self, page_num, total_pages):
        """Draw watermark and footer on each page."""
        self.saveState()
        
        # Watermark
        self.setFont("Helvetica", 60)
        self.setFillColorRGB(0.9, 0.9, 0.9, alpha=0.1)
        self.translate(300, 400)
        self.rotate(45)
        self.drawCentredString(0, 0, "PassGuard")
        
        self.restoreState()
        
        # Footer
        self.setFont("Helvetica", 8)
        self.setFillColorRGB(0.5, 0.5, 0.5)
        self.drawString(inch, 0.5 * inch, f"PassGuard Security Report - Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        self.drawRightString(7.5 * inch, 0.5 * inch, f"Page {page_num} of {total_pages}")


def generate_pdf_report(report: dict, filepath: str) -> None:
    """
    Generate a professional PDF security report.
    
    Args:
        report: Security audit report dict
        filepath: Path to save PDF file
    """
    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        rightMargin=0.75*inch,
        leftMargin=0.75*inch,
        topMargin=0.75*inch,
        bottomMargin=1*inch
    )
    
    # Container for PDF elements
    story = []
    
    # Styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12,
        fontName='Helvetica-Bold'
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=13,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=6,
        fontName='Helvetica'
    )
    
    # Title
    story.append(Paragraph("🔒 PassGuard Security Report", title_style))
    story.append(Paragraph(f"<b>{report['report_name']}</b>", heading_style))
    story.append(Paragraph(f"Generated: {report['timestamp']}", body_style))
    story.append(Spacer(1, 0.3*inch))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    
    stats = report['stats']
    summary_data = [
        ['Metric', 'Count', 'Status'],
        ['Total Credentials', str(stats['total_credentials']), ''],
        ['Reused Passwords', str(stats['reused_passwords']), '🔴 High Risk' if stats['reused_passwords'] > 0 else '✅ Good'],
        ['Weak Passwords', str(stats['weak_passwords']), '🔴 High Risk' if stats['weak_passwords'] > 0 else '✅ Good'],
        ['PII Matches', str(stats['pii_matches']), '🟠 Medium Risk' if stats['pii_matches'] > 0 else '✅ Good'],
        ['Similar Password Groups', str(stats['similarity_groups']), '🟡 Low Risk' if stats['similarity_groups'] > 0 else '✅ Good'],
    ]
    
    summary_table = Table(summary_data, colWidths=[3*inch, 1.5*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Recommendations with colored boxes
    story.append(Paragraph("Priority Recommendations", heading_style))
    story.append(Spacer(1, 0.1*inch))
    
    findings = report['findings']
    
    # Critical weak passwords - RED BOX
    critical_weak = [w for w in findings['weak_passwords'] if w['strength'] == 'critical']
    if critical_weak:
        critical_style = ParagraphStyle(
            'Critical',
            parent=body_style,
            fontSize=11,
            textColor=colors.HexColor('#ffffff'),
            backColor=colors.HexColor('#e74c3c'),
            borderWidth=2,
            borderColor=colors.HexColor('#c0392b'),
            borderPadding=8,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("🔴 CRITICAL - Change Immediately", critical_style))
        story.append(Spacer(1, 0.05*inch))
        
        for item in critical_weak[:10]:
            issues = ', '.join(item['issues'][:2])
            item_style = ParagraphStyle('CriticalItem', parent=body_style, leftIndent=15, textColor=colors.HexColor('#c0392b'))
            story.append(Paragraph(f"<b>• {item['website']}</b> ({item['username']}) - {issues}", item_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Reused passwords - RED BOX
    if findings['reused_passwords']:
        reused_style = ParagraphStyle(
            'Reused',
            parent=body_style,
            fontSize=11,
            textColor=colors.HexColor('#ffffff'),
            backColor=colors.HexColor('#e74c3c'),
            borderWidth=2,
            borderColor=colors.HexColor('#c0392b'),
            borderPadding=8,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("🔴 HIGH RISK - Reused Passwords", reused_style))
        story.append(Spacer(1, 0.05*inch))
        
        for item in findings['reused_passwords'][:5]:
            sites = ', '.join(item['sites'][:5])
            if len(item['sites']) > 5:
                sites += f" (+{len(item['sites'])-5} more)"
            item_style = ParagraphStyle('ReusedItem', parent=body_style, leftIndent=15, textColor=colors.HexColor('#c0392b'))
            story.append(Paragraph(f"<b>• Password {item['masked_password']}</b> used on: {sites}", item_style))
        story.append(Spacer(1, 0.2*inch))
    
    # PII matches - ORANGE BOX
    if findings['pii_matches']:
        pii_style = ParagraphStyle(
            'PII',
            parent=body_style,
            fontSize=11,
            textColor=colors.HexColor('#ffffff'),
            backColor=colors.HexColor('#e67e22'),
            borderWidth=2,
            borderColor=colors.HexColor('#d35400'),
            borderPadding=8,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("🟠 HIGH RISK - Contains Personal Information", pii_style))
        story.append(Spacer(1, 0.05*inch))
        
        for item in findings['pii_matches'][:5]:
            matched = ', '.join(item['matched_fields'][:2])
            item_style = ParagraphStyle('PIIItem', parent=body_style, leftIndent=15, textColor=colors.HexColor('#d35400'))
            story.append(Paragraph(f"<b>• {item['website']}</b> - {matched}", item_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Weak passwords (non-critical) - YELLOW BOX
    weak_only = [w for w in findings['weak_passwords'] if w['strength'] == 'weak']
    if weak_only:
        weak_style = ParagraphStyle(
            'Weak',
            parent=body_style,
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            backColor=colors.HexColor('#f39c12'),
            borderWidth=2,
            borderColor=colors.HexColor('#e67e22'),
            borderPadding=8,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("🟡 MEDIUM RISK - Weak Passwords", weak_style))
        story.append(Spacer(1, 0.1*inch))
        
        weak_data = [['Website', 'Username', 'Entropy', 'Issues']]
        for item in weak_only[:10]:
            issues = ', '.join(item['issues'][:2])
            weak_data.append([
                item['website'][:25],
                item['username'][:20],
                f"{item['entropy']} bits",
                issues[:50]
            ])
        
        weak_table = Table(weak_data, colWidths=[1.8*inch, 1.5*inch, 1*inch, 2.2*inch])
        weak_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f39c12')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#000000')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#d68910')),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fef9e7'), colors.HexColor('#fcf3cf')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        
        story.append(weak_table)
        story.append(Spacer(1, 0.2*inch))
    
    # Similar passwords - YELLOW BOX
    if findings['similarity_groups']:
        similar_style = ParagraphStyle(
            'Similar',
            parent=body_style,
            fontSize=11,
            textColor=colors.HexColor('#000000'),
            backColor=colors.HexColor('#f39c12'),
            borderWidth=2,
            borderColor=colors.HexColor('#e67e22'),
            borderPadding=8,
            fontName='Helvetica-Bold'
        )
        story.append(Paragraph("🟡 MEDIUM RISK - Similar Password Groups", similar_style))
        story.append(Spacer(1, 0.05*inch))
        
        for i, item in enumerate(findings['similarity_groups'][:3], 1):
            sites = ', '.join(item['sites'][:5])
            item_style = ParagraphStyle('SimilarItem', parent=body_style, leftIndent=15, textColor=colors.HexColor('#9a7d0a'))
            story.append(Paragraph(f"<b>• Group {i}:</b> {sites}", item_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Action items
    story.append(PageBreak())
    story.append(Paragraph("Recommended Actions", heading_style))
    
    for i, rec in enumerate(report['recommendations'], 1):
        story.append(Paragraph(f"{i}. {rec}", body_style))
        story.append(Spacer(1, 0.1*inch))
    
    # Security notice
    story.append(Spacer(1, 0.3*inch))
    notice_style = ParagraphStyle(
        'Notice',
        parent=body_style,
        fontSize=9,
        textColor=colors.HexColor('#e74c3c'),
        borderWidth=1,
        borderColor=colors.HexColor('#e74c3c'),
        borderPadding=10,
        backColor=colors.HexColor('#fef5f5')
    )
    story.append(Paragraph(
        "⚠️ <b>SECURITY NOTICE:</b> This report contains sensitive information about your password security. "
        "Store this document securely and do not share it publicly. Passwords are masked but account "
        "information is visible.",
        notice_style
    ))
    
    # Build PDF with watermark
    doc.build(story, canvasmaker=WatermarkCanvas)


def save_report_pdf(report: dict, filepath: str) -> None:
    """
    Save security audit report as PDF.
    
    Args:
        report: Audit report dict
        filepath: Path to save PDF file
    """
    generate_pdf_report(report, filepath)
