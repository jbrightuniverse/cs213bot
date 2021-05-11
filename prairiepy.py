# from https://gitlab.com/astrosticks/prairiepy

'''A Python module aimed at accessing data from a PrairieLearn API server
PrairieLearn: https://www.prairielearn.org/
The PrairieLearn API is documented at: https://prairielearn.readthedocs.io/en/latest/api/
'''
import requests

_DEFAULT_API_SERVER_URL = 'https://www.prairielearn.org/pl/api/v1'

colormap = {
        "red1": (255, 204, 188),
        "red2": (255, 108, 91),
        "red3": (199, 44, 29),
        "pink1": (255, 188, 216),
        "pink2": (250, 92, 152),
        "pink3": (186, 28, 88),
        "purple1": (220, 198, 224),
        "purple2": (155, 89, 182),
        "purple3": (94, 20, 125),
        "blue1": (57, 212, 225),
        "blue2": (18, 151, 224),
        "blue3": (0, 87, 160),
        "turquoise1": (94, 250, 247),
        "turquoise2": (38, 203, 192),
        "turquoise3": (0, 140, 128),
        "green1": (142, 225, 193),
        "green2": (46, 204, 113),
        "green3": (0, 140, 49),
        "yellow1": (253, 227, 167),
        "yellow2": (245, 171, 53),
        "yellow3": (216, 116, 0),
        "orange1": (255, 220, 181),
        "orange2": (255, 146, 106),
        "orange3": (195, 82, 43),
        "brown1": (246, 196, 163),
        "brown2": (206, 156, 123),
        "brown3": (142, 92, 59),
        "gray1": (224, 224, 224),
        "gray2": (144, 144, 144),
        "gray3": (80, 80, 80)
    }

class PrairieLearn:

    # Class methods

    def __init__(
        self, 
        api_key,
        api_server_url=_DEFAULT_API_SERVER_URL,
    ):
        self.api_headers = {
            'Private-Token': str(api_key),
        }

        # Store the url without the ending backslash
        url = api_server_url
        self.api_server_url = url if url[-1] != '/' else url[:-1]

    # API query methods

    def query(self,url):
        '''Returns the response of a PrairieLearn API query'''
        return requests.get(url, headers=self.api_headers)

    # API endpoint wrappers & function decorators
    # Documentation: https://prairielearn.readthedocs.io/en/latest/api#endpoints

    def query_formatted_endpoint(endpoint_wrapper):
        def formatter(self, options):
            endpoint = endpoint_wrapper(self)
            return self.query(self.api_server_url + endpoint.format(**options))
        return formatter

    # Course instance endpoints
    def _route_course_instance(self, endpoint):
        return '/course_instances/{course_instance_id}' + endpoint

    @query_formatted_endpoint
    def get_gradebook(self):
        """All of the data available in the course gradebook, with one entry per user containing summary data on all assessments."""
        return self._route_course_instance('/gradebook')

    @query_formatted_endpoint
    def get_assessments(self):
        """All assessments in the course instance"""
        return self._route_course_instance('/assessments')

    @query_formatted_endpoint
    def get_submission(self):
        """One specific submission"""
        return self._route_course_instance('/submissions/{submission_id}')
    

    # Assessment endpoints

    def _route_assessment(self, endpoint):
        return self._route_course_instance('/assessments/{assessment_id}' + endpoint)

    @query_formatted_endpoint
    def get_assessment(self):
        """One specific assessment"""
        return self._route_assessment('') # The route to an assessment is its own endpoint

    @query_formatted_endpoint
    def get_assessment_instances(self):
        """All assessment instances for a given assessment"""
        return self._route_assessment('/assessment_instances')
    
    @query_formatted_endpoint
    def get_assessment_access_rules(self):
        """All assessment access rules for a given assessment"""
        return self._route_assessment('/assessment_access_rules')


    # Assessment instance endpoints

    def _route_assessment_instance(self, endpoint):
        return self._route_course_instance('/assessment_instances/{assessment_instance_id}' + endpoint)

    @query_formatted_endpoint
    def get_assessment_instance(self):
        """One specific assessment instance"""
        return self._route_assessment_instance('') # The route to an assessment instance is its own endpoint
    
    @query_formatted_endpoint
    def get_instance_questions(self):
        """All instance questions for a given assessment instance"""
        return self._route_assessment_instance('/instance_questions')

    @query_formatted_endpoint
    def get_assessment_instance_submissions(self):
        """All submissions for a given assessment instance"""
        return self._route_assessment_instance('/submissions')

    @query_formatted_endpoint
    def get_assessment_instance_log(self):
        """The event log for a specific assessment"""
        return self._route_assessment_instance('/log')
