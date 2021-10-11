<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaPublishing</%block>

<%block name="blkDialogHeader">
  Publishing Application on Verge3D Network...
</%block>

<%block name="blkDialogContent">

  <div class="spinner-preloader-cont">
    <div class="spinner-preloader-percentage" id='publishingPercentage'>0%</div>
    <div class="spinner-preloader"></div>
  </div>

  <button class="button" id="stopUploading">Cancel</button>
  
</%block>

<%block name="blkDialogScript">
  ${parent.blkDialogScript()}

  stopUploading.addEventListener('click', function(event) {
      makeRequest('/storage/net/?req=cancel', null, null);
  });
</%block>

