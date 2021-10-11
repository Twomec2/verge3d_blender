<%def name="parseError(msg)">

<%

MESSAGE_CODES = {
  'NET_ERR_TIME_SKEWED': '''The difference between your local system time and the server time is too large.
This is considered as a security issue and thus your request was denied.
Please correct your local system time and try again.''',
  'NET_ERR_CANCELLED': 'Upload request cancelled.',
  'NET_ERR_NOTHING': 'There are no files to upload to Verge3D Network.'
}

%>

% if msg in MESSAGE_CODES:
  ${MESSAGE_CODES[msg]}
% else:
  ${msg}
% endif

</%def>
