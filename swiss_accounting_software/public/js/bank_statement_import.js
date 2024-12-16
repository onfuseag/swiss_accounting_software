frappe.ui.form.on("Bank Statement Import", {
    
    custom_convert_xml_to_csv(frm,cdt,cdn){
        
        frappe.call({
                method: "swiss_accounting_software.camt_erpnext.bank_statement_import.convert_xml_to_csv",
                args: {
                    file: frm.doc.custom_camt_xml_file
                                
        },callback: function (r) {


            var value = r.message
            var value_path = value.split('private/files/')
            console.log("this is value path "+ value_path)

            let imagefile = new FormData()
            imagefile.append('file_url','/private/files/'+value_path[1])
            imagefile.append('is_private', "1")
            console.log(imagefile)

            fetch('/api/method/upload_file',{
                headers:{
                    
                    'X-Frappe-CSRF-Token':frappe.csrf_token
                },
                method:'POST',
                body:imagefile,


            })
            .then(res=>res.json())
            .then(data=>{
                console.log(data)
                console.log(data.message.file_name)	
                    $.ajax({
                        url:`/api/resource/Bank Statement Import/${frm.doc.name}`,
                        type:'PUT',
                        headers:{
                        'Content-Type':'application/json',
                        'X-Frappe-CSRF-Token':frappe.csrf_token
                        },
                        data:JSON.stringify({import_file:data.message.file_url}),
                        success:function(data){
                                return data
                        },
                        error:function(data){
                                return data
                        }
                    })
                    .then(res=>res.json())
                        .then(dataa=>{
                            console.log(dataa)
                        })
                    })
                }
            });
            frm.save();
        },
    }
);