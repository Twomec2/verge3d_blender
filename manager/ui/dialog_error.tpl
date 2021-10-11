<%inherit file="dialog.tpl"/>
<%namespace name="utils" file="utils.tpl"/>

<%block name="blkDialogId">diaError</%block>

<%block name="blkDialogHeader">
  % if message.startswith('NET_'):
    Verge3D Network Operation Failed
  % else:
    Operation Failed
  %endif
</%block>

<%block name="blkDialogContent">
  <div class="dialog-text">
    ${utils.parseError(message)}
  </div>
  <button id="diaErrorOk" class="button">Got it!</button>
</%block>

<%block name="blkDialogScript">
  diaErrorClose.addEventListener('click', function() { destroyDialog("diaError"); });
  diaErrorOk.addEventListener('click', function() { destroyDialog("diaError"); });

  focusElem('diaErrorOk');
</%block>
