<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaLicenseKey</%block>

<%block name="blkDialogHeader">
  Enter License Key
</%block>

<%block name="blkDialogContent">
  <form action="/enterkey/" id="enterKeyForm">
    <div class="dialog-text-center">Copy your license key and paste it below:</div>
    <input type="text" name="key" value="" class="dialog-key-input" placeholder="XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX">
    <input type="submit" value="Activate" class="button key">
  </form>
</%block>

<%block name="blkDialogScript">
  ${parent.blkDialogScript()}

  enterKeyForm.addEventListener('submit', function(event) {

      var formData = new FormData(enterKeyForm);

      makeRequest('/enterkey/', formData, function(response) {
          closeDialog('diaLicenseKey');
          var dia = appendDialog(response);
          openDialog(dia);
      });

      event.preventDefault();
  });
</%block>

