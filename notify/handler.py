# Copyright (C) 2013 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Request Handler for /notify endpoint."""

__author__ = 'alainv@google.com (Alain Vongsouvanh)'


import io
import json
import logging
import webapp2

from random import choice
from apiclient.http import MediaIoBaseUpload
from oauth2client.appengine import StorageByKeyName

from model import Credentials
import util
import urllib2


CAT_UTTERANCES = [
    "<em class='green'>Purr...</em>",
    "<em class='red'>Hisss... scratch...</em>",
    "<em class='yellow'>Meow...</em>"
]


class NotifyHandler(webapp2.RequestHandler):
  """Request Handler for notification pings."""

  def post(self):
    """Handles notification pings."""
    logging.info('Got a notification with payload %s', self.request.body)
    data = json.loads(self.request.body)
    userid = data['userToken']
    # TODO: Check that the userToken is a valid userToken.
    self.mirror_service = util.create_service(
        'mirror', 'v1',
        StorageByKeyName(Credentials, userid, 'credentials').get())
    if data.get('collection') == 'locations':
      self._handle_locations_notification(data)
    elif data.get('collection') == 'timeline':
      self._handle_timeline_notification(data)

  def _handle_locations_notification(self, data):
    """Handle locations notification."""
    location = self.mirror_service.locations().get(id=data['itemId']).execute()
    '''text = 'Gaze says you are at %s by %s.' % \
        (location.get('latitude'), location.get('longitude'))
    body = {
        'text': text,
        'location': location,
        'menuItems': [{'action': 'NAVIGATE'},
                      {'action': 'DELETE'}],
        'notification': {'level': 'DEFAULT'}
    }'''


    latitude = str(location.get('latitude'))
    longitude = str(location.get('longitude'))
    giventag = "beautiful"
    logging.warning('Watch out!')

    data = json.load(urllib2.urlopen('https://api.instagram.com/v1/media/search?lat='+latitude+'&lng='+longitude+'&distance=10&access_token=257974112.b828a5d.1090e8d181b64d81a2d653d2dc60ffcd'))
    if not data['data']:
      logging.warning('Nothing within 10m')
      data = json.load(urllib2.urlopen('https://api.instagram.com/v1/media/search?lat='+latitude+'&lng='+longitude+'&distance=50&access_token=257974112.b828a5d.1090e8d181b64d81a2d653d2dc60ffcd'))
      if not data['data']:
        logging.warning('Nothing within 50m')
        data = json.load(urllib2.urlopen('https://api.instagram.com/v1/media/search?lat='+latitude+'&lng='+longitude+'&distance=100&access_token=257974112.b828a5d.1090e8d181b64d81a2d653d2dc60ffcd'))

    tagfound = False
    anytag = False
    for index, item in list(enumerate(data['data'])):
      if not item['users_in_photo']:
        if item['tags']:
          for tag in item['tags']:
            if tag is giventag:
              closestphoto = data['data'][index]
              tagfound = True
          if not tagfound:
            closestphoto = data['data'][index]
            anytag = True
        if not tagfound and not anytag:
            closestphoto = data['data'][index]

    logging.warning(closestphoto)
    pic = closestphoto['images']['standard_resolution']['url']
    #distance = closestphoto['distance']
    #data = json.load(urllib2.urlopen('https://api.instagram.com/v1/media/search?lat=42.056889&lng=-87.676521&distance=100&access_token=257974112.b828a5d.1090e8d181b64d81a2d653d2dc60ffcd'))
    #loc = json.load(urllib2.urlopen("https://api.instagram.com/v1/locations/search?lat="+latitude+"&lng="+longitude+"&access_token=257974112.b828a5d.1090e8d181b64d81a2d653d2dc60ffcd"))
    #locid = loc['data'][0]['id']
    #closephotos = json.load(urllib2.urlopen('https://api.instagram.com/v1/locations/'+locid+'/media/recent?access_token=257974112.b828a5d.1090e8d181b64d81a2d653d2dc60ffcd'))
    #closestphoto = closephotos['data'][0]['images']['standard_resolution']['url']
    #data = api.media_search(lat='42.03320',lng='-87.672122')
    #media = api.media(data[0].text)
    #closestphoto = data['data'][0]['images']['standard_resolution']['url']

    GAZE_CARD = """ <article class="photo">
                      <img src=""" + pic + """ width="360px" height="360px">
                    </article>
                """


    body = {
        'html': GAZE_CARD,
        'menuItems': [{'action': 'DELETE'},
                      {'action': 'CUSTOM',
                        'id': 'complete',
                        'values': [{
                          'displayName': 'Complete'
                        }]
                      }],
        'notification': {'level': 'DEFAULT'}
    }
    #if self.request.get('html') == 'on':
      # body['html'] = [self.request.get('message')]
      #body['html'] = GAZE_CARD
    #else:
      #body['text'] = self.request.get('message')

    # self.mirror_service is initialized in util.auth_required.
    self.mirror_service.timeline().insert(body=body).execute()
    
    # self.mirror_service.timeline().insert(body=body).execute()

  def _handle_timeline_notification(self, data):
    """Handle timeline notification."""
    for user_action in data.get('userActions', []):
      # Fetch the timeline item.
      item = self.mirror_service.timeline().get(id=data['itemId']).execute()

      if user_action.get('type') == 'SHARE':
        # Create a dictionary with just the attributes that we want to patch.
        body = {
            'text': 'Python Quick Start got your photo! %s' % item.get('text', '')
        }

        # Patch the item. Notice that since we retrieved the entire item above
        # in order to access the caption, we could have just changed the text
        # in place and used the update method, but we wanted to illustrate the
        # patch method here.
        self.mirror_service.timeline().patch(
            id=data['itemId'], body=body).execute()

        # Only handle the first successful action.
        break
      elif user_action.get('type') == 'LAUNCH':
        # Grab the spoken text from the timeline card and update the card with
        # an HTML response (deleting the text as well).
        note_text = item.get('text', '');
        utterance = choice(CAT_UTTERANCES)

        item['text'] = None
        item['html'] = ("<article class='auto-paginate'>" +
            "<p class='text-auto-size'>" +
            "Oh, did you say " + note_text + "? " + utterance + "</p>" +
            "<footer><p>Python Quick Start</p></footer></article>")
        item['menuItems'] = [{ 'action': 'DELETE' }];

        self.mirror_service.timeline().update(
            id=item['id'], body=item).execute()
      else:
        logging.info(
            "I don't know what to do with this notification: %s", user_action)


NOTIFY_ROUTES = [
    ('/notify', NotifyHandler)
]
