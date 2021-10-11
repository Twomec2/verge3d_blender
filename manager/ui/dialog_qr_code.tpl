<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaQRCode</%block>

<%block name="blkDialogHeader">
  App QR Code
</%block>

<%block name="blkDialogContent">
  <img width=300 height=300 src="" id="qrCodeImage">
</%block>

<%block name="blkDialogScript">
  document.getElementById('diaQRCodeClose').addEventListener('click', function() {
      closeDialog('diaQRCode');
      openDialog('diaPublished');
  });
</%block>
