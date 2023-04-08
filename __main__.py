from base64 import b64decode
from datetime import datetime
import json
from os import environ

from bs4 import BeautifulSoup
from google.cloud import bigquery
import requests


def parse_percentage_str(str):
  '''
  Parses data representing a percentage. It can optionally have a plus-or-minus
  portion and optionally have a less-than or greater-than portion. Because it
  can optionally have a less-than or greater-than portion, the part of the data
  that can have that portion is returned as a string instead of as an int. It
  can also optionally have a unicode arrow character representing the increase
  or decrease of the data compared to the previous period. Because this data
  doesn't need to be recorded, because increases and decreases can be
  calculated as needed over time, this data is dropped.

  Examples:

  <19% ± 3%▼ is returned as: { 'prefix': '<', percentage: 19, 'plus_minus': 3 }

  <19% ± 3% is returned as: { 'prefix': '<', percentage: 19, 'plus_minus': 3 }

  19% ± 3% is returned as { percentage: 19, 'plus_minus': 3 }

  <19% is returned as { 'prefix': '<', percentage: 19 }

  19% is returned as { percentage: 19 }
  '''

  # Remove the up arrow and down arrow characters, if they exist.
  str = str.replace('▼', '').replace('▲', '')

  # Split the string into parts.
  parts = str.split(' ')

  # If the first part is a prefix, save it. Remove it. But, because the prefix
  # is not a part in the parts list, and is instead the first character of the
  # first part, remove it from the first part.
  prefix = None
  if parts[0][0] == '<' or parts[0][0] == '>':
    prefix = parts[0][0]
    parts[0] = parts[0][1:]

  # At this point, the first part is guaranteed to be the percentage. Save it.
  percentage = int(parts[0][:-1])

  # If there is a plus-or-minus part, save it.
  plus_minus = None
  if len(parts) > 1:
    plus_minus = int(parts[2].replace('%', ''))

  return {
    'prefix': prefix,
    'percentage': percentage,
    'plus_minus': plus_minus,
  }


def popular_vote_projection(soup):
  '''
  Parses the popular vote projection data from the web page and returns it as a
  list of dicts.
  '''

  # Find the list of elements in the graphic for vote data. Filter it to only
  # text and rect elements. Exclude the first and last elements (which do not
  # contain data.
  els = soup.html.find('svg', id='indexvote').find_all(['text', 'rect'])[1:][:-1]

  # Split the list of elements into list of party element groups. Also, remove
  # the first two elements of the group, because they contain SVG graphic data,
  # not vote data.
  p_el_grps = [els[i+2:i+4] for i in range(0, (len(els)//4)*4, 4)]

  # Convert those elements to a dict with data.
  party_data_raw = [{
    'party': p_els[1].string,
    'data': parse_percentage_str(p_els[0].string),
  } for p_els in p_el_grps]

  # Parse the string parts of the data into the data we need. Note that for
  # vote projections, there is no prefix like < or > before the percentage.
  # We end up with data like:
  # [{
  #   'party': 'CPC',
  #   'vote_percent': 34,
  #   'plus_or_minus_percent': 4,
  # }]
  party_data = [{
    'party': p['party'],
    'vote_percent': p['data']['percentage'],
    'plus_or_minus_percent': p['data']['plus_minus'],
  } for p in party_data_raw]

  return party_data


def seat_projection(soup):
  '''
  Parses the seat projection data from the web page and returns it as a list of
  dicts.
  '''

  # Find the list of elements in the graphic for seat data. Filter it to only
  # text and rect elements. Exclude the first and last elements (which do not
  # contain data.
  els = soup.html.find('svg', id='indexseats').find_all(['text', 'rect'])[1:][:-1]

  # Split the list of elements into list of party element groups. Also, remove
  # the first two elements of the group, because they contain SVG graphic data,
  # not seat data.
  p_el_grps = [els[i+2:i+4] for i in range(0, (len(els)//4)*4, 4)]

  # Convert those elements to a dict with data.
  party_data_raw = [{
    'party': p_els[1].string,
    'data': f"{p_els[0].string.split(']')[0]}]",
  } for p_els in p_el_grps]

  # Parse the string parts of the data into the data we need.
  # We end up with data like:
  # [{
  #   'party': 'CPC',
  #   'min': 114,
  #   'mid': 140,
  #   'max': 174,
  # }]
  party_data = [{
      'party': p['party'],
      'min': int(p['data'].split(' ')[1].split('-')[0][1:]),
      'mid': int(p['data'].split(' ')[0]),
      'max': int(p['data'].split(' ')[1].split('-')[1][:-1]),
  } for p in party_data_raw]

  return party_data


def odds_winning_most_seats_projection(soup):
  '''
  Parses the odds of winning most seats projection data from the web page and
  returns it as a list of dicts.
  '''

  # Find the list of elements in the graphic for vote data. Filter it to only
  # text and rect elements. Exclude the first and last elements (which do not
  # contain data.
  els = soup.html.find_all('svg', id='indexodds')[0].find_all('text')[3:][:-1]

  # Split the list of elements into list of party element groups. Also, remove
  # the first two elements of the group, because they contain SVG graphic data,
  # not vote data.
  p_el_grps = [els[i:i+2] for i in range(0, (len(els)//2)*2, 2)]

  # Convert those elements to a dict with data.
  odds_data_raw = [{
    'party': grp[1].string,
    'data': parse_percentage_str(grp[0].string),
  } for grp in p_el_grps]

  # Parse the string parts of the data into the data we need.
  # We end up with data like:
  # [{
  #   'party': 'CPC',
  #   'odds_percent_raw': 65,
  # }]
  party_data = [{
    'party': o['party'],
    # TODO: Change the database schema this data will be written into to use a
    # struct instead of a string so that we can store the prefix and the number
    # separately. For now, store the prefix and number together in a string
    # because that's what the database schema expects.
    'odds_percent_raw': o['data']['percentage'] if o['data']['prefix'] == None else f"{o['data']['prefix']}{o['data']['percentage']}",
  } for o in odds_data_raw]

  return party_data


def odds_outcome_projection(soup):
  '''
  Parses the odds of winning most seats projection data from the web page and
  returns it as a list of dicts.
  '''

  # Find the list of elements in the graphic for vote data. Filter it to only
  # text and rect elements. Exclude the first and last elements (which do not
  # contain data.
  els = soup.html.find_all('svg', id='indexodds')[1].find_all('text')[3:][:-1]

  # Split the list of elements into list of party element groups. Also, remove
  # the first two elements of the group, because they contain SVG graphic data,
  # not vote data.
  p_el_grps = [els[i:i+2] for i in range(0, (len(els)//2)*2, 2)]

  # Convert those elements to a dict with data.
  outcome_data_raw = [{
    'outcome': grp[1].string,
    'data': parse_percentage_str(grp[0].string),
  } for grp in p_el_grps]

  # Parse the string parts of the data into the data we need.
  # We end up with data like:
  # [{
  #   'party': 'CPC',
  #   'odds_percent_raw': '<65',
  # }]
  outcome_data = [{
    'outcome': o['outcome'],
    # TODO: Change the database schema this data will be written into to use a
    # struct instead of a string so that we can store the prefix and the number
    # separately. For now, store the prefix and number together in a string
    # because that's what the database schema expects.
    'odds_percent_raw': o['data']['percentage'] if o['data']['prefix'] == None else f"{o['data']['prefix']}{o['data']['percentage']}",
  } for o in outcome_data_raw]

  return outcome_data


def coalition_seat_projection(soup):
  '''
  Parses the coalition seat projection data from the web page and returns it as
  a list of dicts.
  '''

  # Find the list of elements in the graphic for vote data. Filter it to only
  # text and rect elements. Exclude the first and last elements (which do not
  # contain data.
  els = soup.html.find('svg', id='coalitionseats').find_all('text')[:-3]

  # Split the list of elements into list of party element groups. Also, remove
  # the first two elements of the group, because they contain SVG graphic data,
  # not vote data.
  c_el_grps = [els[i:i+2] for i in range(0, (len(els)//2)*2, 2)]

  # Convert those elements to a dict with data.
  coalition_data_raw = [{
    'coalition': c[0].string,
    'seats': c[1].string,
  } for c in c_el_grps]

  # Parse the string parts of the data into the data we need.
  # We end up with data like:
  # [{
  #   'coalition': 'CPC+BQ',
  #   'seats': 177,
  # }]
  coalition_data = [{
      'coalition': c['coalition'],
      'seats': c['seats'],
  } for c in coalition_data_raw]

  return coalition_data


def coalition_odds_projection(soup):
  '''
  Parses the coalition odds projection data from the web page and returns it as
  a list of dicts.
  '''

  # Find the list of elements in the graphic for vote data. Filter it to only
  # text. Skip some elements at the beginning and end of the list to filter to
  # only elements that contain data (excluding elements used for styling the
  # SVG).
  els = soup.html.find('svg', id='coalitionodds').find_all('text')[2:][:-2]

  # Split the list of elements into list of party element groups. Also, remove
  # the first two elements of the group, because they contain SVG graphic data,
  # not vote data.
  c_el_grps = [els[i:i+2] for i in range(0, (len(els)//2)*2, 2)]

  # Convert those elements to a dict with data.
  coalition_data_raw = [{
    'coalition': c[1].string,
    'data': c[0].string,
  } for c in c_el_grps]

  # Parse the string parts of the data into the data we need.
  # We end up with data like:
  # [{
  #   'party': 'CPC+BQ',
  #   'odds_percent_raw': 62%,
  # }]
  coalition_data = [{
      'coalition': c['coalition'],
      'odds_percent_raw': c['data'][:-1],
  } for c in coalition_data_raw]

  return coalition_data

# This is the entry point for the scraper. It is called by the OpenWhisk
# runtime when the scraper is invoked.
def main(args):
  '''
  Main function for the scraper. Uses the functions defined above that parse
  the data from the web page and writes it to a BigQuery table.
  '''

  # Decode and write GCP creds to disk
  decoded_creds = b64decode(args['gcp_creds']).decode('utf-8')
  bq_client = bigquery.Client.from_service_account_info(json.loads(decoded_creds))

  # Fetch data from 338Canada site and make a parser.
  response = requests.get('https://338canada.com/')
  soup = BeautifulSoup(response.content, 'html.parser')

  # Re-use the parsed DOM to parse all of the data needed.
  vote_proj = popular_vote_projection(soup)
  seat_proj = seat_projection(soup)
  odds_most_seats_proj = odds_winning_most_seats_projection(soup)
  odds_outcome_proj = odds_outcome_projection(soup)
  coalition_seat_proj = coalition_seat_projection(soup)
  coalition_odds_proj = coalition_odds_projection(soup)

  # Also extract the date the projection was published from the web page.
  months = {
    'January': 1,
    'February': 2,
    'March': 3,
    'April': 4,
    'May': 5,
    'June': 6,
    'July': 7,
    'August': 8,
    'September': 9,
    'October': 10,
    'November': 11,
    'December': 12,
  }
  date_el = soup.html.find('main').center.find('a', href='#', target='_blank')
  split = date_el.string.split(' ')[2:]
  d = {
    'month': months[split[0]],
    'day': int(split[1][:-1]),
    'year': int(split[2]),
  }
  day_str = f"{d['year']}-{str(d['month']).zfill(2)}-{str(d['day']).zfill(2)}"

  # Use the parsed data with the BigQuery SDK to stream a row into the table.
  # client = bigquery.Client()
  rows_to_insert = [
    {
      'day': day_str,
      'vote': vote_proj,
      'seat': seat_proj,
      'odds_most_seats': odds_most_seats_proj,
      'odds_outcome': odds_outcome_proj,
      'coalition_seat': coalition_seat_proj,
      'coalition_odds_most_seats': coalition_odds_proj,
      'inserted_at': datetime.utcnow().isoformat(),
    },
  ]
  print('Will insert the following data:', rows_to_insert)
  errors = bq_client.insert_rows_json('public-datasets-363301.canada_338_projections.records', rows_to_insert)
  if errors == []:
      print("The row was added.")
  else:
      raise Exception("Encountered errors while inserting rows: {}".format(errors))

# This is a way to invoke the entry point locally for testing. It should be
# commented out when deploying to OpenWhisk.
main({
  'gcp_creds': environ['GCP_CREDS']
})
