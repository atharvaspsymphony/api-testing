import logging
import requests
import json
import streamlit as st
import socketio

# Streamlit app layout
st.title("API Testing")

# API configuration inputs
api_url_options = {
    "D1 (https://developers.symphonyfintech.in)": "https://developers.symphonyfintech.in",
    "T1 (http://103.181.209.198:11091)": "http://103.181.209.198:11091",
    "T2 (http://103.181.209.198:10431)": "http://103.181.209.198:10431",
    "T3 (http://103.181.209.198:11021)": "http://103.181.209.198:11021",
    "T4 (http://103.69.170.23:10954)": "http://103.69.170.23:10954"
}

# Dropdown for selecting API URL
selected_url_label = st.selectbox("Select API URL", list(api_url_options.keys()))
url = api_url_options[selected_url_label] + '/apimarketdata'

secretKey = st.text_input("Secret Key", value='Pxrw554$zH')
appKey = st.text_input("App Key", value='caf0e727f0887e7a597911')
token = st.text_input("Token", value=None)
headers = {'Content-Type': 'application/json'}

# Initialize session state for headers, token, and other states
if 'headers' not in st.session_state:
    st.session_state.headers = headers.copy()
if 'token' not in st.session_state:
    st.session_state.token = ''
if 'user_id' not in st.session_state:
    st.session_state.user_id = ''
if 'socket_data' not in st.session_state:
    st.session_state.socket_data = []

# Function to authenticate
def authenticate(url, secretKey, appKey):
    login_payload = {
        'secretKey': secretKey,
        'appKey': appKey,
        'source': 'WebAPI'
    }
    response = requests.post(url + '/auth/login', headers=headers, data=json.dumps(login_payload), verify=False)
    if response.status_code == 200:
        st.session_state.user_id = response.json()['result']['userID']
        return response.json()['result']['token']
    else:
        return None

# Function to display response
def display_response(response):
    if response is not None and response.status_code == 200:
        st.json(response.json())
    else:
        st.error("Request failed!")

# Login button
if st.button("Login"):
    if token is None:
        token = authenticate(url, secretKey, appKey)
    if token:
        st.session_state.token = token
        st.session_state.headers['Authorization'] = token
        st.success("Login successful! Token: {}".format(token))
    else:
        st.error("Login failed!")

# Function to handle API requests with expanders
def api_request(label, payload_example, api_endpoint, method='GET', pass_payload=True):
    with st.expander(label):
        if pass_payload:
            payload = st.text_area(f"JSON Payload for {label}", height=100, value=json.dumps(payload_example, indent=4))
        else:
            payload = None

        if st.button(f"Send {label} Request"):
            if method == 'GET':
                response = requests.get(url + api_endpoint, headers=st.session_state.headers, params=json.loads(payload) if payload else None)
            elif method == 'POST':
                response = requests.post(url + api_endpoint, headers=st.session_state.headers, data=payload if payload else None, verify=False)
            elif method == 'PUT':
                response = requests.put(url + api_endpoint, headers=st.session_state.headers, data=payload if payload else None, verify=False)
            elif method == 'DELETE':
                response = requests.delete(url + api_endpoint, headers=st.session_state.headers, verify=False)
            display_response(response)

# API Requests using expanders
# No payload for 'Get Client Config'
api_request("Get Client Config", {}, '/config/clientConfig', method='GET', pass_payload=False)

api_request("Get Instruments Master", {"exchangeSegmentList": ["NSEFO"]}, '/instruments/master', method='POST')

api_request("Get Quotes", {"instruments": [{"exchangeSegment": 1, "exchangeInstrumentID": 26000}],"xtsMessageCode": 1502,"publishFormat": "JSON"}, '/instruments/quotes', method='POST')

api_request("Get Series", {"exchangeSegment": 2}, '/instruments/instrument/series')

api_request("Get Equity Symbol", {"exchangeSegment": 1, "series": "EQ", "symbol": "RELIANCE"}, '/instruments/instrument/symbol')

api_request("Get Expiry Data", {"exchangeSegment": 2, "series": "OPTIDX", "symbol": "NIFTY"}, '/instruments/instrument/expiryDate')

api_request("Get Future Symbol", {"exchangeSegment": 2, "series": "FUTIDX", "symbol": "NIFTY", "expiryDate": "26Sep2024"}, '/instruments/instrument/futureSymbol')

api_request("Get Option Symbol", {"exchangeSegment": 2, "series": "OPTIDX", "symbol": "BANKNIFTY", "expiryDate": "25Sep2024", "optionType": "CE", "strikePrice": "50500"}, '/instruments/instrument/optionSymbol')

api_request("Get Strike Price", {"exchangeSegment": 2, "series": "OPTIDX", "symbol": "BANKNIFTY", "expiryDate": "25Sep2024", "optionType": "CE"}, '/instruments/instrument/strikePrice')

api_request("Get Option Type", {"exchangeSegment": 2, "series": "OPTIDX", "symbol": "BANKNIFTY", "expiryDate": "25Sep2024"}, '/instruments/instrument/optionType')

api_request("Get Index List", {"exchangeSegment": 1}, '/instruments/indexlist')

api_request("Search Instrument by ID", {"instruments": [{"exchangeSegment": 2, "exchangeInstrumentID": 35089}], "source": "WebAPI"}, '/search/instrumentsbyid', method='POST')

api_request("Search Instrument by String", {"searchString": "TCS"}, '/search/instruments')

api_request("Subscribe", {"instruments": [{"exchangeSegment": 1, "exchangeInstrumentID": 26000}], "xtsMessageCode": 1501}, "/instruments/subscription", method='POST')

api_request("UnSubscribe", {"instruments": [{"exchangeSegment": 1, "exchangeInstrumentID": 2885}], "xtsMessageCode": 1501}, "/instruments/subscription", method='PUT')

api_request("Get OHLC Data", {"exchangeSegment": 1,"exchangeInstrumentID": 2885,"startTime": "Sep 20 2024 091500","endTime": "Sep 20 2024 100000","compressionValue": 60}, '/instruments/ohlc')

# No payload for 'Logout'
api_request("Logout", {}, '/auth/logout', method='DELETE', pass_payload=False)

# WebSocket client class
class DataSocket(socketio.Client):
    def __init__(self, token, user_id, url):
        super().__init__(logger=False, engineio_logger=False, ssl_verify=False)
        self.token = token
        self.user_id = user_id
        self.url = url
        self.broadcastMode = 'Full'
        self.connection_url = f'{self.url}/?token={token}&userID={user_id}&publishFormat=JSON&broadcastMode={self.broadcastMode}'
        self.register_handlers()

    def register_handlers(self):
        self.on('connect', self.on_connect)
        self.on('message', self.on_message)
        self.on('1512-json-full', self.tickdata)
        self.on('disconnect', self.on_disconnect)
        self.on('error', self.error)

    def connect_socket(self):
        self.connect(self.connection_url, transports='websocket', namespaces=None, socketio_path='/apimarketdata/socket.io')
        self.wait()

    def on_connect(self):
        print('Connected to Socket')

    def on_message(self, data):
        print("Message received:", data)

    def tickdata(self, data):
        print(data)
    
    def on_disconnect(self):
        print('Disconnected from Socket')
    
    def error(self):
        print("Error in socket")

# Display WebSocket connection option
with st.expander("WebSocket"):
    st.write("WebSocket connection....(Work in progress)")
    user_id = st.text_input("UserID", value=None)
    broadcastMode = 'Full'
    # Uncomment the following lines once WebSocket implementation is complete
    # if user_id:
    #     if st.button("Test Connection with User ID"):
    #         socket_client = DataSocket(st.session_state.token, user_id, url)
    #         socket_client.connect_socket()
    # else:
    #     if st.button("Test Connection with Session User ID"):
    #         socket_client = DataSocket(st.session_state.token, st.session_state.user_id, url)
    #         socket_client.connect_socket()
