<%inherit file="dialog.tpl"/>

<%block name="blkDialogId">diaLicense</%block>

<%block name="blkDialogHeader">
  Verge3D Licensing Manager
</%block>

<%block name="blkDialogContent">
  <div class='license-info-cont'>
    % if licenseInfo['type'] == 'TRIAL':
      <div class="dialog-text-center red">You are currently using the trial version of Verge3D.</div>

      <div class="dialog-text-center">
        Please make sure to acquire a license before you start using this software in production.
      </div>

      <div class="dialog-text-center">
        Read about the benefits and limitations of Verge3D Trial <a href="https://www.soft8soft.com/verge3d-trial/" target="_blank" class="colored-link">here</a>.
      </div>

    % elif licenseInfo['maintenance']:
      <div class="dialog-text-center green">
        Your Verge3D ${'for ' + licenseInfo['modPackage'].title() if licenseInfo['modPackage'] != 'ALL' else ''} ${licenseInfo['type'].title()} License is active.
      </div>
      <div class="dialog-text-center">
        You are eligible for receiving software updates and support until ${licenseInfo['validUntil'].strftime('%d %b %Y')}.
      </div>

    % else:
      <div class="dialog-text-center red">
        Your software maintenance subscription expired on ${licenseInfo['validUntil'].date().strftime('%d %B %Y')}.
      </div>

      % if licenseInfo['renewalGracePeriod'] > 0:
        <div class="dialog-text-center">
          It is only left ${licenseInfo['renewalGracePeriod']} days from your grace period to renew your subscription with 50% discount.
        </div>
      % endif

      <div class="dialog-text-center">
        Please consider renewing your Verge3D subscription.
      </div>

    % endif
  </div>

  % if licenseInfo['maintenance']:
    <button id="enterKey" class="button" title="Enter the license key">Enter New Key</button>
  % else:
    <div class="two-buttons license-two-buttons">
      <div>
        <a href="javascript:void(0);" id="enterKey" class="button-like" title="Enter the license key">Enter Key</a>
      </div>

      <div>
        % if licenseInfo['type'] == 'TRIAL':
          <a href="https://www.soft8soft.com/licensing/" target="_blank" class="button-like" title="Open Soft8Soft licensing page">Purchase</a>
        % elif licenseInfo['maintenance'] == False:
          <a href="https://www.soft8soft.com/verge3d-subscription-renewal/" target="_blank" class="button-like" title="Find out more about Verge3D subscription renewal">Renewal Info</a>
        % endif
      </div>
    </div>
  % endif

</%block>

<%block name="blkDialogScript">
  ${parent.blkDialogScript()}

  enterKey.addEventListener('click', function() {
      closeDialog('diaLicense');
      openDialog('diaLicenseKey');
  });
</%block>
