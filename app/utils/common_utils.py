from urllib.parse import urlparse



def parse_url_path(urlpath):
    """
    remove scheme and host name out from url.
    """
    pr = urlparse(urlpath)
    toremove = f"{pr.scheme}://{pr.netloc}/"
    return pr.geturl().replace(toremove, '', 1)


def get_part_of_day(hour):
    return ("morning" if 5 <= hour <= 11
            else
            "afternoon" if 12 <= hour <= 17
            else
            "evening" if 18 <= hour <= 22
            else
            "night")
