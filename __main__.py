from bs4 import BeautifulSoup
from datetime import datetime
from google.cloud import bigquery
import requests


# from test_html import html as html_doc


def popular_vote_projection(soup):
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
    'data': p_els[0].string,
  } for p_els in p_el_grps]

  # Parse the string parts of the data into the data we need.
  # We end up with data like:
  # [{
  #   'party': 'CPC',
  #   'vote_percent': 34,
  #   'plus_or_minus_percent': 4,
  # }]
  party_data = [{
      'party': p['party'],
      'vote_percent': int(p['data'].split(' ')[0][:-1]),
      'plus_or_minus_percent': int(p['data'].split(' ')[2][:-1]),
  } for p in party_data_raw]

  return party_data


def seat_projection(soup):
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
    'data': p_els[0].string,
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
  # Find the list of elements in the graphic for vote data. Filter it to only
  # text and rect elements. Exclude the first and last elements (which do not
  # contain data.
  els = soup.html.find_all('svg', id='indexodds')[0].find_all('text')[3:][:-1]

  # Split the list of elements into list of party element groups. Also, remove
  # the first two elements of the group, because they contain SVG graphic data,
  # not vote data.
  p_el_grps = [els[i:i+2] for i in range(0, (len(els)//2)*2, 2)]

  # Convert those elements to a dict with data.
  party_data_raw = [{
    'party': grp[1].string,
    'data': grp[0].string,
  } for grp in p_el_grps]

  # Parse the string parts of the data into the data we need.
  # We end up with data like:
  # [{
  #   'party': 'CPC',
  #   'odds': 65,
  # }]
  party_data = [{
      'party': p['party'],
      'odds_percent_raw': p['data'][:-1],
  } for p in party_data_raw]

  return party_data


def odds_outcome_projection(soup):
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
    'data': grp[0].string,
  } for grp in p_el_grps]

  # Parse the string parts of the data into the data we need.
  # We end up with data like:
  # [{
  #   'party': 'CPC',
  #   'odds': 65,
  # }]
  outcome_data = [{
      'outcome': o['outcome'],
      'odds_percent_raw': o['data'][:-1],
  } for o in outcome_data_raw]

  return outcome_data


def coalition_seat_projection(soup):
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


def main(args):
  # Fetch data from 338Canada site and make a parser.
  response = requests.get('https://338canada.com/')
  soup = BeautifulSoup(response.text, 'html.parser')

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
  client = bigquery.Client()
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
  errors = client.insert_rows_json('public-datasets-363301.canada_338_projections.records', rows_to_insert)
  if errors == []:
      print("The row was added.")
  else:
      raise Exception("Encountered errors while inserting rows: {}".format(errors))
