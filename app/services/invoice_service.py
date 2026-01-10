import io
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.units import inch

def generate_invoice_pdf(
    billing_data: dict,
    tenant_data: dict,
    company_details: dict = None
) -> bytes:
    """
    Generates a professional PDF invoice in memory.
    
    billing_data: {
        'invoice_number': str,
        'date': str,
        'amount': float,
        'tax': float,
        'discount': float,
        'total': float,
        'currency': str,
        'plan_name': str
    }
    tenant_data: {
        'name': str,
        'email': str,
        'address': str (optional)
    }
    company_details: {
        'name': str,
        'address': str,
        'email': str,
        'website': str
    }
    """
    if not company_details:
        company_details = {
            'name': 'Antigravity SaaS Platform',
            'address': '123 Tech Lane, Silicon Valley, CA 94025',
            'email': 'billing@antigravity.ai',
            'website': 'www.antigravity.ai'
        }

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=12
    )
    
    label_style = ParagraphStyle(
        'LabelStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.grey,
        spaceAfter=2
    )
    
    value_style = ParagraphStyle(
        'ValueStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.black,
        spaceAfter=10
    )

    elements = []

    # Header: Title and Invoice Number
    elements.append(Paragraph("INVOICE", title_style))
    elements.append(Paragraph(f"Invoice #: {billing_data.get('invoice_number', 'N/A')}", styles['Normal']))
    elements.append(Paragraph(f"Date: {billing_data.get('date', datetime.now().strftime('%Y-%m-%d'))}", styles['Normal']))
    elements.append(Spacer(1, 0.5 * inch))

    # Billing Info: Two columns (Sender and Receiver)
    data = [
        [Paragraph("<b>FROM:</b>", label_style), Paragraph("<b>TO:</b>", label_style)],
        [
            Paragraph(f"{company_details['name']}<br/>{company_details['address']}<br/>{company_details['email']}<br/>{company_details['website']}", styles['Normal']),
            Paragraph(f"{tenant_data['name']}<br/>{tenant_data['email']}<br/>{tenant_data.get('address', '')}", styles['Normal'])
        ]
    ]
    
    info_table = Table(data, colWidths=[3 * inch, 3 * inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 12),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 0.4 * inch))

    # Items Table
    item_header = ["Description", "Quantity", "Rate", "Amount"]
    plan_name = billing_data.get('plan_name', 'SaaS Subscription')
    currency = billing_data.get('currency', 'INR')
    
    items_data = [
        item_header,
        [plan_name, "1", f"{currency} {billing_data['amount']:,.2f}", f"{currency} {billing_data['amount']:,.2f}"]
    ]
    
    items_table = Table(items_data, colWidths=[3 * inch, 1 * inch, 1.2 * inch, 1.3 * inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#f1f5f9")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.HexColor("#334155")),
        ('ALIGN', (0,0), (-1,0), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('ALIGN', (1,1), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,0), 0.5, colors.grey),
        ('LINEBELOW', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 0.2 * inch))

    # Totals Section
    subtotal = billing_data['amount']
    tax = billing_data.get('tax', 0.0)
    discount = billing_data.get('discount', 0.0)
    total = billing_data.get('total', subtotal + tax - discount)

    summary_data = [
        ["Subtotal", f"{currency} {subtotal:,.2f}"],
        ["Tax", f"{currency} {tax:,.2f}"],
        ["Discount", f"-{currency} {discount:,.2f}"],
        [Paragraph("<b>TOTAL</b>", styles['Normal']), Paragraph(f"<b>{currency} {total:,.2f}</b>", styles['Normal'])]
    ]
    
    summary_table = Table(summary_data, colWidths=[4.7 * inch, 1.3 * inch])
    summary_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('LINEABOVE', (0,3), (1,3), 1, colors.black),
    ]))
    elements.append(summary_table)

    # Footer
    elements.append(Spacer(1, 1 * inch))
    elements.append(Paragraph("Thank you for your business!", styles['Italic']))
    elements.append(Paragraph("If you have any questions, please contact our support team.", styles['Normal']))

    doc.build(elements)
    
    return buffer.getvalue()
