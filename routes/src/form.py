from PyPDF2.generic import BooleanObject, NameObject, IndirectObject


def set_need_appearances_writer(writer):
    try:
        catalog = writer._root_object
        # get the AcroForm tree and add "/NeedAppearances attribute
        if "/AcroForm" not in catalog:
            writer._root_object.update({
                NameObject("/AcroForm"): IndirectObject(len(writer._objects), 0, writer)})
        need_appearances = NameObject("/NeedAppearances")
        writer._root_object["/AcroForm"][need_appearances] = BooleanObject(True)
        return writer
    except Exception as e:
        print('set_need_appearances_writer() catch : ', repr(e))
        return writer


def update_checkbox_values(page, fields):
    for j in range(0, len(page['/Annots'])):
        writer_annot = page['/Annots'][j].getObject()
        for field in fields:
            if writer_annot.get('/T') == field:
                writer_annot.update({
                    NameObject("/V"): NameObject(fields[field]),
                    NameObject("/AS"): NameObject(fields[field])
                })
