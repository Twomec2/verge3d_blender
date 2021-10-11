<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaLicenseKeyDone</%block>

<%block name="blkDialogHeader">
  Licensing Activation Status
</%block>

<%block name="blkDialogContent">

  % if licenseInfo['type'] == 'OUTDATED':

    <div class="dialog-text-center red">
      Your software maintenance subscription expired on ${licenseInfo['validUntil'].date().strftime('%d %B %Y')}.
    </div>

    <div class="dialog-text">
      Please consider <a href="https://www.soft8soft.com/verge3d-subscription-renewal/" target="_blank" class="colored-link">renewing</a> your subscription or
      <a href="https://www.soft8soft.com/verge3d-download-archive/" target="_blank" class="colored-link">stick</a> to Verge3D version issued prior the expiration date.
    </div>

    <button id="diaLicenseKeyDoneOk" class="button">Ok</button>

  % else:

    <div class="dialog-text">
      Your Verge3D ${'for ' + licenseInfo['modPackage'].title() if licenseInfo['modPackage'] != 'ALL' else ''} ${licenseInfo['type'].title()} License has been activated.
    </div>
    <div class="dialog-text-center">
      Thank you for choosing Verge3D!
    </div>

    <button id="diaLicenseKeyDoneOk" class="button">Awesome!</button>

    % if licenseInfo['type'] == 'TRIAL':
      <div class="dialog-text red">
        Please note that the key you just entered is intended for preview purposes only.
        The key will expire after 30 day period. Make sure you purchase a license for use in production.
      </div>
    % endif

  % endif
</%block>

<%block name="blkDialogScript">
  diaLicenseKeyDoneClose.addEventListener('click', function() {
      destroyDialog('diaLicenseKeyDone');
      document.location.reload(true);
  });

  diaLicenseKeyDoneOk.addEventListener('click', function() {
      destroyDialog('diaLicenseKeyDone');
      document.location.reload(true);
  });

  focusElem('diaLicenseKeyDoneOk');
</%block>
