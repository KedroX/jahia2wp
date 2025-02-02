"""(c) All rights reserved. ECOLE POLYTECHNIQUE FEDERALE DE LAUSANNE, Switzerland, VPSI, 2017"""
import logging
from datetime import datetime
from urllib import parse
from urllib.parse import urlencode
from xml.dom import minidom
from parser.box_sorted_group import BoxSortedGroup
from bs4 import BeautifulSoup
from django.utils.text import slugify

from utils import Utils


class Box:
    """A Jahia Box. Can be of type text, infoscience, etc."""

    # WP box types
    TYPE_TEXT = "text"
    TYPE_ONE_COL_CONTAINER = "oneColContainer"
    TYPE_COLORED_TEXT = "coloredText"
    TYPE_PEOPLE_LIST = "peopleList"
    TYPE_INFOSCIENCE = "infoscience"
    TYPE_INFOSCIENCE_FILTER = "infoscienceFilter"
    TYPE_ACTU = "actu"
    TYPE_MEMENTO = "memento"
    TYPE_FAQ = "faq"
    TYPE_TOGGLE = "toggle"
    TYPE_INCLUDE = "include"
    TYPE_CONTACT = "contact"
    TYPE_XML = "xml"
    TYPE_LINKS = "links"
    TYPE_RSS = "rss"
    TYPE_FILES = "files"
    TYPE_BUTTONS = "buttons_box"
    TYPE_SNIPPETS = "snippets"
    TYPE_SYNTAX_HIGHLIGHT = "syntaxHighlight"
    TYPE_KEY_VISUAL = "keyVisual"
    TYPE_MAP = "map"
    TYPE_GRID = "grid"

    # Mapping of known box types from Jahia to WP
    types = {
        "epfl:textBox": TYPE_TEXT,
        "epfl:coloredTextBox": TYPE_COLORED_TEXT,
        "epfl:peopleListBox": TYPE_PEOPLE_LIST,
        "epfl:infoscienceBox": TYPE_INFOSCIENCE,
        "epfl:infoscienceFilteredBox": TYPE_INFOSCIENCE_FILTER,
        "epfl:actuBox": TYPE_ACTU,
        "epfl:mementoBox": TYPE_MEMENTO,
        "epfl:faqBox": TYPE_FAQ,
        "epfl:toggleBox": TYPE_TOGGLE,
        "epfl:htmlBox": TYPE_INCLUDE,
        "epfl:contactBox": TYPE_CONTACT,
        "epfl:xmlBox": TYPE_XML,
        "epfl:linksBox": TYPE_LINKS,
        "epfl:rssBox": TYPE_RSS,
        "epfl:filesBox": TYPE_FILES,
        "epfl:bigButtonsBox": TYPE_BUTTONS,
        "epfl:smallButtonsBox": TYPE_BUTTONS,
        "epfl:snippetsBox": TYPE_SNIPPETS,
        "epfl:syntaxHighlightBox": TYPE_SYNTAX_HIGHLIGHT,
        "epfl:keyVisualBox": TYPE_KEY_VISUAL,
        "epfl:mapBox": TYPE_MAP,
        "epfl:gridBox": TYPE_GRID,
        "epfl:oneColContainer": TYPE_ONE_COL_CONTAINER
    }

    UPDATE_LANG = "UPDATE_LANG_BY_EXPORTER"

    def __init__(self, site, page_content, element, multibox=False, is_in_sidebar=False):
        """

        :param site: instance of Site class
        :param page_content: instance of PageContent class. This is the page content containing current box
        :param element: DOM element <extra> or <main>
        :param multibox:
        """
        # attributes
        self.site = site
        self.page_content = page_content
        self.type = ""
        self.shortcode_name = ""
        self.set_type(element)
        self.title = Utils.get_tag_attribute(element, "boxTitle", "jahia:value")
        self.content = ""
        self.sort_group = None
        self.is_in_sidebar = False

        # the shortcode attributes with URLs that must be fixed by the wp_exporter
        self.shortcode_attributes_to_fix = []

        # parse the content
        if self.type:
            self.set_content(element, multibox)

    def set_sort_infos(self, element):
        """
        Tells if element needs to be sort or not. We check if it has a parent of type "mainList" with a
        "jahia:sortHandler" attribute which is not empty

        :param element: Element to check.
        :return:
        """
        if element.parentNode.nodeName == 'mainList':

            sort_params = element.parentNode.getAttribute("jahia:sortHandler")

            # If we have parameters for sorting
            if sort_params != "":
                # We get sortHandler uuid to identify it so it will be unique
                uuid = element.parentNode.getAttribute("jcr:uuid")
                # Getting (or creating) sortHandler. It may already exists if another box use it.
                self.sort_group = self.site.get_box_sort_group(uuid, sort_params)

                # Generate name of field in which we have to look for sort value
                sort_field = "jcr:{}".format(self.sort_group.sort_field)

                sort_value = element.getAttribute(sort_field)

                # Add box to sort handler
                self.sort_group.add_box_to_sort(self, sort_value)

    def set_type(self, element):
        """
        Sets the box type
        """
        type = element.getAttribute("jcr:primaryType")

        if not type:
            logging.warning("Box has no type")
        elif type in self.types:
            self.type = self.types[type]
        else:
            self.type = type

    def set_content(self, element, multibox=False):
        """set the box attributes"""

        # Init sort handler if needed
        self.set_sort_infos(element)

        # text
        if self.type in [self.TYPE_TEXT, self.TYPE_COLORED_TEXT, self.TYPE_ONE_COL_CONTAINER]:
            self.set_box_text(element, multibox)
        # people list
        elif self.TYPE_PEOPLE_LIST == self.type:
            self.set_box_people_list(element)
        # infoscience
        elif self.TYPE_INFOSCIENCE == self.type or self.TYPE_INFOSCIENCE_FILTER == self.type:
            self.set_box_infoscience(element)
        # actu
        elif self.TYPE_ACTU == self.type:
            self.set_box_actu(element)
        # memento
        elif self.TYPE_MEMENTO == self.type:
            self.set_box_memento(element)
        # faq
        elif self.TYPE_FAQ == self.type:
            self.set_box_faq(element)
        # toggle
        elif self.TYPE_TOGGLE == self.type:
            self.set_box_toggle(element)
        # include
        elif self.TYPE_INCLUDE == self.type:
            self.set_box_include(element)
        # contact
        elif self.TYPE_CONTACT == self.type:
            self.set_box_contact(element)
        # xml
        elif self.TYPE_XML == self.type:
            self.set_box_xml(element)
        # links
        elif self.TYPE_LINKS == self.type:
            self.set_box_links(element)
        # rss
        elif self.TYPE_RSS == self.type:
            self.set_box_rss(element)
        # files
        elif self.TYPE_FILES == self.type:
            self.set_box_files(element)
        # small/bigButtonsBox
        elif self.TYPE_BUTTONS == self.type:
            self.set_box_buttons(element)
        # snippets
        elif self.TYPE_SNIPPETS == self.type:
            self.set_box_snippets(element)
        # syntaxHighlight
        elif self.TYPE_SYNTAX_HIGHLIGHT == self.type:
            self.set_box_syntax_highlight(element)
        # keyVisual
        elif self.TYPE_KEY_VISUAL == self.type:
            self.set_box_key_visuals(element)
        # Map
        elif self.TYPE_MAP == self.type:
            self.set_box_map(element)
        # Grid
        elif self.TYPE_GRID == self.type:
            self.set_box_grid(element)
        # unknown
        else:
            self.set_box_unknown(element)

        self.fix_video_iframes()

        self.add_id_to_h3()

        self.fix_img_align_left()

    def _set_scheduler_box(self, element, content):
        """set the attributes of a scheduler box"""

        self.shortcode_name = "epfl_scheduler"

        start_datetime = Utils.get_tag_attribute(element, "comboList", "jahia:validFrom")
        end_datetime = Utils.get_tag_attribute(element, "comboList", "jahia:validTo")

        if not start_datetime and not end_datetime:
            logging.info("Scheduler has no start date and no end date, simply using content")
            return content

        today = datetime.now().strftime("%Y-%m-%d")

        start_date = ""
        start_time = ""

        if "T" in start_datetime:
            start_date = start_datetime.split("T")[0]
            start_time = start_datetime.split("T")[1]

        end_date = ""
        end_time = ""

        if "T" in end_datetime:
            end_date = end_datetime.split("T")[0]
            end_time = end_datetime.split("T")[1]

        # check if we have a start date in the past and no end date
        if start_date and not end_date:
            if start_date < today:
                logging.info("Scheduler has a start date in the past ({}) and no end date,"
                             " simply using content".format(start_date))
                return content

        # we don't need to check if end_date > today
        # In case end_date < today the shortcode display nothing
        if not start_date and end_date:
            start_date = today

        return '[{} start_date="{}" end_date="{}" start_time="{}" end_time="{}"]{}[/{}]'.format(
            self.shortcode_name,
            start_date,
            end_date,
            start_time,
            end_time,
            content,
            self.shortcode_name
        )

    def set_box_grid(self, element):
        """
        Set attributes for a grid box.
        A grid box is a <div> containing others <div> with a specified size (defined by the layout, "large" or
        "default"), image, text and link.
        FIXME: Handle <boxTitle> field (was empty when box support has been added so no idea how it is displayed..)
        FIXME: Handle <text> field (was empty when box support has been added so no idea how it is displayed..)
        FIXME: Handle attribute GridListList -> "jahia:sortHandler" if needed
        :param element:
        :return:
        """
        shortcode_outer_name = "epfl_grid"
        shortcode_inner_name = "epfl_gridElem"

        self.shortcode_name = shortcode_outer_name

        # register the shortcodes
        self.site.register_shortcode(shortcode_inner_name, ["link", "image"], self)

        self.content = '[{}]\n'.format(shortcode_outer_name)

        elements = element.getElementsByTagName("gridList")

        for e in elements:

            layout_infos = Utils.get_tag_attribute(e, "layout", "jahia:value")
            soup = BeautifulSoup(layout_infos, 'html5lib')
            layout = soup.find('jahia-resource').get('default-value')

            # Retrieve info
            link = Utils.get_tag_attribute(e, "jahia:url", "jahia:value")
            image = Utils.get_tag_attribute(e, "image", "jahia:value")
            title = Utils.get_tag_attribute(e, "jahia:url", "jahia:title")

            # Escape if necessary
            title = Utils.handle_custom_chars(title)

            self.content += '[{} layout="{}" link="{}" title="{}" image="{}"][/{}]\n'.format(
                shortcode_inner_name, layout, link, title, image, shortcode_inner_name)

        self.content += "[/{}]".format(shortcode_outer_name)

    def set_box_text(self, element, multibox=False):
        """set the attributes of a text box
            A text box can have two forms, either it contains just a <text> tag
            or it contains a <comboListList> which contains <comboList> tags which
            contain <text>, <filesList>, <linksList> tags. The last two tags may miss from time
            to time because the jahia export is not perfect.
            FIXME: filesList and linksList are processed in a given order. It may correspond to export but they also
            may be switched. So maybe we will have to correct it in the future.
        """
        def filter_and_transform(box_content):
            """ Sometimes we don't want to crawl the data as it is given"""
            # for Twitter
            if 'twitter-timeline' in box_content:
                soup = BeautifulSoup(box_content, 'html5lib')
                links = soup.findAll("a", {"class": "twitter-timeline"})

                if links:
                    for link in links:
                        if link.get('href') and link['href']:
                            next_script_tag = link.find_next("script")
                            link.replace_with('[epfl_twitter url="{}"]\n'.format(link['href']))
                            # remove next script tag if it is twitter related
                            if 'twitter-wjs' in next_script_tag.text:
                                next_script_tag.extract()
                    box_content = ''.join(['%s' % x for x in soup.body.contents]).strip()
            return box_content

        if not multibox:
            content = Utils.get_tag_attribute(element, "text", "jahia:value")
            content = filter_and_transform(content)

            files_list = element.getElementsByTagName("filesList")
            if files_list:
                content += self._parse_files_to_list(files_list[0])

            links_list = element.getElementsByTagName("linksList")
            if links_list:
                content += self._parse_links_to_list(links_list[0])
        else:

            # Looking for sort information. If found, they looks like :
            # "created;desc;true;true"
            sort_infos = Utils.get_tag_attribute(element, "comboListList", "jahia:sortHandler")

            # If we have information about sorting, we extract them
            if sort_infos != "":
                # It seems that sort field is corresponding to "jcr:<sort_field>" attribute in XML
                sort_field = sort_infos.split(";")[0]
                sort_way = sort_infos.split(";")[1]
            else:
                # To sort by index to keep the correct order.
                sort_way = "asc"

            # If we don't have information about sorting, we still have to keep boxes order. So index will
            # be used to add each encountered boxes at an index.
            box_index = 0

            box_list = {}

            combo_list = element.getElementsByTagName("comboList")
            for combo in combo_list:
                # We generate box content
                box_content = Utils.get_tag_attribute(combo, "text", "jahia:value")
                # filesList and linksList contain <link> tags exactly like linksBox, so we can just reuse
                # the same code used to parse linksBox.
                box_content += self._parse_files_to_list(combo)
                box_content += self._parse_links_to_list(combo)

                if box_content == '':
                    continue

                # if we have sort infos, we have to get field information in XML
                if sort_infos != "":
                    box_key = combo.getAttribute('jcr:{}'.format(sort_field))

                    # If key is empty, we switch back to "sortless" mode. Otherwise, if all boxes have empty keys
                    # (which is probably the case), every box we add to the list will erase the previous one because
                    # they all have the same key...
                    if box_key == '':
                        sort_infos = ""
                        sort_way = "asc"
                        box_key = box_index
                        box_index += 1
                else:
                    box_key = box_index
                    box_index += 1
                # Saving box content with sort field association
                box_list[box_key] = box_content

            # We sort boxes with correct information. As output, we will have a list of Tuples with dict key as
            # first element (index 0) and dict value as second element (index 1)
            box_list = sorted(box_list.items(), reverse=(sort_way == 'desc'))

            # For all boxes content
            content = ""

            for box_key, box_content in box_list:
                content += filter_and_transform(box_content)

            # scheduler shortcode
            if Utils.get_tag_attribute(element, "comboList", "jahia:ruleType") == "START_AND_END_DATE":
                content = self._set_scheduler_box(element, content)

        self.content = content

    @staticmethod
    def _extract_epfl_news_parameters(url):
        """
        Extract parameters form url
        """
        parameters = parse.parse_qs(parse.urlparse(url).query)

        if 'channel' in parameters:
            channel_id = parameters['channel'][0]
        else:
            channel_id = ""
            logging.error("News Shortcode - channel ID is missing")

        if 'lang' in parameters:
            lang = parameters['lang'][0]

            # With Jahia, it is possible to also use "french" language denomination, we change it back to english
            if lang == 'ang':
                lang = 'en'
            if lang == 'fra':
                lang = 'fr'

        else:
            lang = ""
            logging.warning("News Shortcode - lang is missing")

        if 'template' in parameters:
            template = parameters['template'][0]
        else:
            template = ""
            logging.warning("News Shortcode - template is missing")

        # in actu.epfl.ch if sticker parameter exists, sticker is not displayed
        # (whatever the value of sticker parameter)
        # if sticker parameter does not exist, sticker is displayed
        if 'sticker' in parameters:
            stickers = "no"
        else:
            stickers = "yes"

        category = ""
        if 'category' in parameters:
            category = parameters['category'][0]

        themes = ""
        if 'themes' in parameters:
            themes = parameters['theme']

        projects = ""
        if 'project' in parameters:
            projects = parameters['project']

        return channel_id, lang, template, category, themes, stickers, projects

    def set_box_people_list(self, element):
        """
        Set the attributes of a people list box

        More information here:
        https://c4science.ch/source/kis-jahia6-dev/browse/master/core/src/main/webapp/common/box/display/peopleListBoxDisplay.jsp
        """
        self.shortcode_name = "epfl_people"

        BASE_URL = "https://people.epfl.ch/cgi-bin/getProfiles?"

        # prepare a dictionary with all GET parameters
        parameters = {}

        # parse the unit parameter
        parameters['unit'] = Utils.get_tag_attribute(element, "query", "jahia:value")

        # parse the template html
        template_html = Utils.get_tag_attribute(element, "template", "jahia:value")

        # Check if "function" exists (it's a filter for information)
        function = Utils.get_tag_attribute(element, "function", "jahia:value")

        if function:
            parameters['function'] = function

        # check if we have an HTML template
        if not template_html:
            logging.warning("epfl_people: no HTML template set")
            self.content = "[epfl_people error: no HTML template set]"
            return

        # extract template key
        template_key = Utils.get_tag_attribute(
            minidom.parseString(template_html),
            "jahia-resource",
            "key"
        )

        # these rules are extracted from jsp of jahia
        if template_key == 'epfl_peopleListContainer.template.default_bloc':
            parameters['struct'] = 1
            template = 'default_struct_bloc'
        elif template_key == 'epfl_peopleListContainer.template.default_bloc_simple':
            template = 'default_bloc'
        elif template_key == 'epfl_peopleListContainer.template.default_list':
            template = 'default_list'
        else:
            template = Utils.get_tag_attribute(minidom.parseString(template_html), "jahia-resource", "key")
        parameters['tmpl'] = "WP_" + template

        # in the parser we can't know the current language.
        # so we assign a string that we will replace by the current language in the exporter
        parameters['lang'] = self.UPDATE_LANG

        url = "{}{}".format(BASE_URL, urlencode(parameters))
        self.content = '[{} url="{}" /]'.format(self.shortcode_name, url)

    def set_box_actu(self, element):
        """set the attributes of an actu box"""

        self.shortcode_name = "epfl_news"

        # We specifically get 'actuListList' node before getting 'url' node in case of several 'url' nodes
        # under 'element'. This happen for lspm website which has a 'snippetBox' inside 'actuBox'...
        actu_list_list = element.getElementsByTagName("actuListList")
        # extract parameters from the old url of webservice
        channel_id, lang, template, category, themes, stickers, projects = self._extract_epfl_news_parameters(
            Utils.get_tag_attribute(actu_list_list[0], "url", "jahia:value")
        )

        # We look for <moreUrl> information
        more_url_list = actu_list_list[0].getElementsByTagName("moreUrl")

        if more_url_list:
            more_url = Utils.get_tag_attribute(more_url_list[0], "jahia:url", "jahia:value")
            more_title = Utils.get_tag_attribute(more_url_list[0], "jahia:url", "jahia:title")
        else:
            more_url = ""
            more_title = ""

        # We look for <rssUrl> information
        rss_url_list = actu_list_list[0].getElementsByTagName("rssUrl")

        if rss_url_list:
            rss_url = Utils.get_tag_attribute(rss_url_list[0], "jahia:url", "jahia:value")
            rss_title = Utils.get_tag_attribute(rss_url_list[0], "jahia:url", "jahia:title")
        else:
            rss_url = ""
            rss_title = ""

        content = ""

        # Title is only for boxes in pages
        if not self.is_in_sidebar:
            content += '<h3>{}</h3>'.format(self.title)

        content += '[{} channel="{}" lang="{}" template="{}" '.format(
            self.shortcode_name,
            channel_id,
            lang,
            template
        )
        if category:
            content += 'category="{}" '.format(category)
        if themes:
            content += 'themes="{}" '.format(",".join(themes))
        if stickers:
            content += 'stickers="{}" '.format(stickers)
        if projects:
            content += 'projects="{}" '.format(",".join(projects))

        content += '/]'

        # If we have a <moreUrl> or <rssUrl> element
        if (more_url and more_title) or (rss_url and rss_title):
            content += '[epfl_buttons_container]'

            if more_url and more_title:
                content += self._get_button_shortcode('small',
                                                      more_url,
                                                      more_title,
                                                      more_title,
                                                      small_button_key='forward')

            if rss_url and rss_title:
                content += self._get_button_shortcode('small',
                                                      rss_url,
                                                      rss_title,
                                                      rss_title,
                                                      small_button_key='forward')

            content += '[/epfl_buttons_container]'

        self.content = content

    @staticmethod
    def _extract_epfl_memento_parameters(url):
        """
        Extract parameters form url
        """
        parameters = parse.parse_qs(parse.urlparse(url).query)

        if 'memento' in parameters:
            memento_name = parameters['memento'][0]
        else:
            memento_name = ""
            logging.error("Memento Shortcode - event ID is missing")

        if 'lang' in parameters:
            lang = parameters['lang'][0]
        else:
            lang = ""
            logging.error("Memento Shortcode - lang is missing")

        if 'template' in parameters:
            template = parameters['template'][0]
        else:
            template = ""
            logging.error("Memento Shortcode - template is missing")

        period = ""
        if 'period' in parameters:
            if parameters['period'][0] == "2":
                period = "upcoming"
            else:
                period = "past"

        color = ""
        if 'color' in parameters:
            color = parameters['color'][0]

        filters = ""
        if 'filters' in parameters:
            filters = parameters['filters'][0]

        category = ""
        if 'category' in parameters:
            category = parameters['category'][0]

        reorder = ""
        if 'reorder' in parameters:
            reorder = parameters['reorder'][0]

        return memento_name, lang, template, period, color, filters, category, reorder

    def set_box_memento(self, element):
        """set the attributes of a memento box"""

        # extract parameters from the old url of webservice
        memento_name, lang, template, period, color, filters, category, reorder = \
            self._extract_epfl_memento_parameters(
                Utils.get_tag_attribute(element, "url", "jahia:value")
            )

        html_content = ''

        # Look for a title if any
        title = Utils.get_tag_attributes(element, "boxTitle", "jahia:value")

        if title:
            html_content += '<h3>{}</h3> '.format(title[0])

        self.shortcode_name = "epfl_memento"
        html_content += '[{} memento="{}" lang="{}" template="{}" '.format(
            self.shortcode_name,
            memento_name,
            lang,
            template
        )
        if period:
            html_content += 'period="{}" '.format(period)
        if color:
            html_content += 'color="{}" '.format(color)
        if filters:
            html_content += 'keyword="{}" '.format(filters)
        if category:
            html_content += 'category="{}" '.format(category)
        if reorder:
            html_content += 'reorder="{}" '.format(reorder)

        html_content += '/]'

        self.content = html_content

    def set_box_infoscience(self, element):
        """
        set the attributes of a infoscience box.
        The "element" parameter can be type "epfl:infoscienceBox" or "epfl:htmlBox". If its an "infoscienceBox",
        we have to look for <url> tags inside <infoscienceListList> tag. And if it's a "htmlBox", we have to look
        inside <importHtmlList> tag. But, in "infoscienceBox", a tag <importHtmlList> can be present and we have to
        ignore it otherwise we will take too much information to display (for "lms" website, we have both tags and
        only <infoscienceListList> content is displayed on Jahia so it indicates we have to ignore <importHtmlList>
        tag.
        :param element: DOM element <main>
        :return:
        """
        # If box have title, we have to display it
        if self.title != "":
            html_content = "<h3>{}</h3>".format(self.title)
        else:
            html_content = ""

        self.shortcode_name = "epfl_infoscience"

        # if "infoscienceBox"
        if self.type == self.TYPE_INFOSCIENCE:
            publication_list = element.getElementsByTagName("infoscienceListList")
        elif self.type == self.TYPE_INFOSCIENCE_FILTER:
            publication_list = element.getElementsByTagName("infoscienceFilteredListList")

        else:  # importHtmlList (self.TYPE_INCLUDE)

            publication_list = element.getElementsByTagName("importHtmlList")

        urls = Utils.get_tag_attributes(publication_list[0], "url", "jahia:value")

        for url in urls:
            html_content += '[{} url="{}"]'.format(self.shortcode_name, url)

        self.content = html_content

    def set_box_faq(self, element):
        """set the attributes of a faq box

        FIXME: Handle boxTitle option
        FIXME: Handle filesList option in FAQ item
        FIXME: Handle linksList option in FAQ item
        """

        shortcode_outer_name = "epfl_faq"
        shortcode_inner_name = "epfl_faqItem"

        self.shortcode_name = shortcode_outer_name

        # register the shortcode
        self.site.register_shortcode(shortcode_inner_name, ["link", "image"], self)

        self.content = '[{}]\n'.format(shortcode_outer_name)

        # Looking for entries
        faq_entries = element.getElementsByTagName("faqList")

        for entry in faq_entries:

            # Get question and escape if necessary
            question = Utils.get_tag_attribute(entry, "question", "jahia:value")
            question = Utils.handle_custom_chars(question)

            # Get answer
            answer = Utils.get_tag_attribute(entry, "answer", "jahia:value")

            self.content += '[{} question="{}"]{}[/{}]\n'.format(
                shortcode_inner_name, question, answer, shortcode_inner_name)

        self.content += "[/{}]".format(shortcode_outer_name)

    def set_box_toggle(self, element):
        """set the attributes of a toggle box"""

        self.shortcode_name = 'epfl_toggle'

        if Utils.get_tag_attribute(element, "opened", "jahia:value") == 'true':
            state = 'open'
        else:
            state = 'close'

        content = '[epfl_toggle title="{}" state="{}"]'.format(self.title, state)
        content += Utils.get_tag_attribute(element, "content", "jahia:value")
        content += '[/epfl_toggle]'

        self.content = content

    def set_box_include(self, element):
        """set the attributes of an include box"""
        url = Utils.get_tag_attribute(element, "url", "jahia:value")
        if "://people.epfl.ch/cgi-bin/getProfiles?" in url:
            url = url.replace("tmpl=", "tmpl=WP_")

            self.shortcode_name = "epfl_people"

            self.content = '[{} url="{}" /]'.format(self.shortcode_name, url)
        elif '://infoscience.epfl.ch/' in url:
            self.set_box_infoscience(element)

        elif '://actu.epfl.ch/' in url:

            self.shortcode_name = "epfl_news"

            # URL looks like https://actu.epfl.ch/webservice/school?channel=8&lang=en&template=3
            parameters = self._extract_epfl_news_parameters(url)

            self.content = '[{} channel="{}" lang="{}" template="{}" ]'.format(self.shortcode_name,
                                                                               parameters[0],
                                                                               parameters[1],
                                                                               parameters[2])

        else:

            self.content = '[remote_content url="{}"]'.format(Utils.get_redirected_url(url))

    def set_box_contact(self, element):
        """set the attributes of a contact box"""

        contact_list = element.getElementsByTagName("contactList")

        content = ""
        # Looping through elements and adding content
        for contact in contact_list:
            content += Utils.get_tag_attribute(contact, "text", "jahia:value")

        self.content = content

    def set_box_xml(self, element):
        """set the attributes of a xml box"""
        xml = Utils.get_tag_attribute(element, "xml", "jahia:value")
        xslt = Utils.get_tag_attribute(element, "xslt", "jahia:value")

        self.shortcode_name = "epfl_xml"

        self.content = '[{} xml="{}" xslt="{}"]'.format(self.shortcode_name, xml, xslt)

    def set_box_rss(self, element):
        """set the attributes of an rss box"""

        # Jahia options
        url = Utils.get_tag_attribute(element, "url", "jahia:value")
        nb_items = Utils.get_tag_attribute(element, "nbItems", "jahia:value")
        hide_title = Utils.get_tag_attribute(element, "hideTitle", "jahia:value")
        detail_items = Utils.get_tag_attribute(element, "detailItems", "jahia:value")

        # check if we have at least an url
        if not url:
            return

        # some values are in JSP tag, with use a default value instead
        if not nb_items.isdigit():
            nb_items = "5"

        # feedzy-rss options
        feeds = url
        max = nb_items
        feed_title = "yes"
        summary = "yes"
        meta = "yes"

        if hide_title == "true":
            feed_title = "no"

        if detail_items != "true":
            summary = "no"
            meta = "no"

        self.content = '[feedzy-rss feeds="{}" max="{}" feed_title="{}" summary="{}" refresh="12_hours" meta="{}"]' \
            .format(feeds, max, feed_title, summary, meta)

    def set_box_links(self, element):
        """set the attributes of a links box"""
        self.content = self._parse_links_to_list(element)

    def set_box_unknown(self, element):
        """set the attributes of an unknown box"""
        self.content = "[{}]".format(element.getAttribute("jcr:primaryType"))

    def set_box_files(self, element):
        """set the attributes of a files box"""
        self.content = self._parse_files_to_list(element)

    def _get_button_shortcode(self, box_type, url, alt_text, text, big_button_image_url="", small_button_key=""):
        """
        Return shortcode text for EPFL button

        :param box_type: 'small' or 'big'
        :param url: URL
        :param alt_text: Text while hovering
        :param text: Link text
        :param big_button_image_url: if box_type=='big', URL to big image
        :param small_button_key: if box_type=='small', key of icon to display
        :return:
        """

        if big_button_image_url:
            big_button_image_url = 'image="{}"'.format(big_button_image_url)

        if small_button_key:
            small_button_key = 'key="{}"'.format(small_button_key)

        # Replacing necessary characters to ensure everything will work correctly
        text = Utils.handle_custom_chars(text)
        alt_text = Utils.handle_custom_chars(alt_text)

        return '[epfl_buttons type="{}" url="{}" {} alt_text="{}" text="{}" {}]'.format(box_type,
                                                                                        url,
                                                                                        big_button_image_url,
                                                                                        alt_text,
                                                                                        text,
                                                                                        small_button_key)

    def set_box_buttons(self, element):

        self.shortcode_name = 'epfl_buttons'

        container_name = 'epfl_buttons_container'

        self.site.register_shortcode(self.shortcode_name, ["image", "url"], self)

        box_type = element.getAttribute("jcr:primaryType")

        if self.title != "":
            content = "<h3>{}</h3>".format(self.title)
        else:
            content = ""

        if 'small' in box_type:
            box_type = 'small'

            button_container = element.getElementsByTagName("smallButtonListList")
            element_name = "smallButtonList"

        else:
            box_type = 'big'
            button_container = element.getElementsByTagName("bigButtonListList")

            element_name = "bigButtonList"

        sort_params = button_container[0].getAttribute("jahia:sortHandler")

        # Default values that may be overrided later
        sort_way = 'asc'
        sort_tag_name = None

        # If we have parameters for sorting, they will look like :
        # epfl_simple_main_bigButtonList_url;desc;false;false
        # Sorting is used on https://dhlab.epfl.ch/page-116974-en.html
        if sort_params != "":
            # Extracting tag name where to find sort info
            # epfl_simple_main_bigButtonList_url;desc;false;false ==> url
            sort_tag_name = sort_params.split(';')[0].split('_')[-1]
            sort_tag_name = "jahia:{}".format(sort_tag_name)

            sort_way = sort_params.split(';')[1]

        button_boxes = BoxSortedGroup('', '', sort_way)

        elements = element.getElementsByTagName(element_name)

        for button_list in elements:
            url = ""
            alt_text = ""
            text = ""
            big_button_image_url = ""
            small_button_key = ""

            # Sorting needed
            if sort_tag_name:
                sort_tags = button_list.getElementsByTagName(sort_tag_name)
                if sort_tags:
                    # It seems that, by default, it is the "jahia:title" value that is used for sorting
                    sort_value = sort_tags[0].getAttribute("jahia:title")

                # We don't have enough information to continue
                if not sort_tags or not sort_value:
                    raise Exception("No sort tag (%s) found (or empty sort value found) for %s",
                                    sort_tag_name, element_name)
            else:
                # No sorting needed, we generate an ID for the box
                sort_value = len(button_boxes.boxes)

            for child in button_list.childNodes:
                if child.ELEMENT_NODE != child.nodeType:
                    continue

                if child.tagName == "label":
                    alt_text = child.getAttribute("jahia:value")

                elif child.tagName == "url":
                    if box_type == 'small':
                        url = child.getAttribute("jahia:value")

                    elif box_type == 'big':
                        for jahia_tag in child.childNodes:
                            if jahia_tag.ELEMENT_NODE != jahia_tag.nodeType:
                                continue

                            text = jahia_tag.getAttribute("jahia:title")

                            if jahia_tag.tagName == "jahia:link":
                                # It happens that a link references a page that does not exist anymore
                                # observed on site dii
                                try:
                                    page = self.site.pages_by_uuid[jahia_tag.getAttribute("jahia:reference")]
                                except KeyError as e:
                                    continue

                                # We generate "Jahia like" URL so exporter will be able to fix it with WordPress URL
                                url = "/page-{}-{}.html".format(page.pid, self.page_content.language)

                            elif jahia_tag.tagName == "jahia:url":
                                url = jahia_tag.getAttribute("jahia:value")

                # 'image' tag is only used for BigButton
                elif child.tagName == "image":
                    # URL is like /content/sites/<site_name>/files/file
                    # splitted gives ['', content, sites, <site_name>, files, file]
                    # result of join is files/file and we add the missing '/' in front.
                    big_button_image_url = '/'.join(child.getAttribute("jahia:value").split("/")[4:])
                    big_button_image_url = '/' + big_button_image_url

                # 'type' tag is only used for SmallButton and is storing reference to image to display
                elif child.tagName == "type":
                    jahia_resource_ref = child.getAttribute("jahia:value")
                    soup = BeautifulSoup(jahia_resource_ref, "lxml")
                    small_button_key = soup.find("jahia-resource").get('default-value')

            if box_type == 'small' and text == "":
                text = alt_text

            # bigButton will have 'image' attribute and smallButton will have 'key' attribute.
            box_content = self._get_button_shortcode(box_type,
                                                     url,
                                                     alt_text,
                                                     text,
                                                     big_button_image_url=big_button_image_url,
                                                     small_button_key=small_button_key)

            # Because boxes can be sortable, we use a BoxSortedGroup to handle this
            button_boxes.add_box_to_sort(box_content, sort_value)

        content = "[{}]".format(container_name)
        content += ''.join(button_boxes.get_sorted_boxes())
        content += "[/{}]".format(container_name)

        self.content = content

    # @classmethod
    # def build_buttons_box_content(cls, box_type, url, image_url, text):
    #     return '[epfl_buttons type="{}" url="{}" image_url="{}" text="{}"]\n'.format(box_type, url, image_url, text)

    def set_box_snippets(self, element):
        """set the attributes of a snippets box"""

        self.shortcode_name = "epfl_snippets"

        # register the shortcode
        self.site.register_shortcode(self.shortcode_name, ["url", "image", "big_image"], self)

        # check if the list is not empty
        if not element.getElementsByTagName("snippetListList"):
            return

        # If box have title, we have to display it
        if self.title != "":
            self.content = "<h3>{}</h3>".format(self.title)
        else:
            self.content = ""

        snippet_list_list = element.getElementsByTagName("snippetListList")[0]

        # Sorting parameters
        sort_params = snippet_list_list.getAttribute("jahia:sortHandler")

        # Default values that may be overrided later
        sort_way = 'asc'
        sort_tag_name = None

        # If we have parameters for sorting, they will look like :
        # epfl_simple_main_snippetList_title;desc;false;false
        # https://pel.epfl.ch/awards_en
        if sort_params != "":
            # Extracting tag name where to find sort info
            # epfl_simple_main_snippetList_title;desc;false;false ==> url
            sort_tag_name = sort_params.split(';')[0].split('_')[-1]

            sort_way = sort_params.split(';')[1]

        snippet_boxes = BoxSortedGroup('', '', sort_way)

        snippets = snippet_list_list.getElementsByTagName("snippetList")

        # Sorting needed
        if sort_tag_name:

            # we first loop through all elements to ensuire we have required sort information
            for snippet in snippets:
                sort_tags = snippet.getElementsByTagName(sort_tag_name)
                if sort_tags:
                    # It seems that, by default, it is the "jahia:value" value that is used for sorting
                    sort_value = sort_tags[0].getAttribute("jahia:value")

                # We don't have enough information to continue
                if not sort_tags or not sort_value:
                    logging.error("No sort tag (%s) found (or empty sort value found) for Snippets. Disabling sorting",
                                  sort_tag_name)
                    # We set to None to disable sorting
                    sort_tag_name = None
                    break

        for snippet in snippets:
            title = Utils.get_tag_attribute(snippet, "title", "jahia:value")
            subtitle = Utils.get_tag_attribute(snippet, "subtitle", "jahia:value")
            description = Utils.get_tag_attribute(snippet, "description", "jahia:value")
            image = Utils.get_tag_attribute(snippet, "image", "jahia:value")
            big_image = Utils.get_tag_attribute(snippet, "bigImage", "jahia:value")
            enable_zoom = Utils.get_tag_attribute(snippet, "enableImageZoom", "jahia:value")

            # Fix path if necessary
            if "/files" in image:
                image = image[image.rfind("/files"):]
            if "/files" in big_image:
                big_image = big_image[big_image.rfind("/files"):]

            # escape
            title = Utils.handle_custom_chars(title)
            subtitle = Utils.handle_custom_chars(subtitle)

            url = ""

            # Sorting needed
            if sort_tag_name:
                # We don't have to check if we have a correct value for "sort_tags" because we already did it while
                # checking sorting information availability
                sort_tags = snippet.getElementsByTagName(sort_tag_name)

                # It seems that, by default, it is the "jahia:value" value that is used for sorting
                sort_value = sort_tags[0].getAttribute("jahia:value")

            else:
                # No sorting needed, we generate an ID for the box
                sort_value = len(snippet_boxes.boxes)

            # url
            if element.getElementsByTagName("url"):
                # first check if we have a <jahia:url> (external url)
                url = Utils.get_tag_attribute(snippet, "jahia:url", "jahia:value")

                # if we have an url, set the subtitle with the url title if empty subtitle
                if url != "":
                    if not subtitle or subtitle == "":
                        subtitle = Utils.get_tag_attribute(snippet, "jahia:url", "jahia:title")
                        subtitle = Utils.handle_custom_chars(subtitle)
                # if not we might have a <jahia:link> (internal url)
                else:
                    uuid = Utils.get_tag_attribute(snippet, "jahia:link", "jahia:reference")

                    if uuid in self.site.pages_by_uuid:
                        page = self.site.pages_by_uuid[uuid]

                        # We generate "Jahia like" URL so exporter will be able to fix it with WordPress URL
                        url = "/page-{}-{}.html".format(page.pid, self.page_content.language)

                        # if link has a title, add it to content as ref
                        url_title = Utils.get_tag_attribute(snippet, "jahia:link", "jahia:title")
                        if url_title and not url_title == "":
                            description += '<a href="' + url + '">' + Utils.handle_custom_chars(url_title) + '</a>'

            box_content = '[{} url="{}" title="{}" subtitle="{}" image="{}"' \
                          ' big_image="{}" enable_zoom="{}"]{}[/{}]'.format(self.shortcode_name,
                                                                            url,
                                                                            title,
                                                                            subtitle,
                                                                            image,
                                                                            big_image,
                                                                            enable_zoom,
                                                                            description,
                                                                            self.shortcode_name)

            # Because boxes can be sortable, we use a BoxSortedGroup to handle this
            snippet_boxes.add_box_to_sort(box_content, sort_value)

        self.content += ''.join(snippet_boxes.get_sorted_boxes())

    def set_box_syntax_highlight(self, element):
        """Set the attributes of a syntaxHighlight box"""
        content = "[enlighter]"
        content += Utils.get_tag_attribute(element, "code", "jahia:value")
        content += "[/enlighter]"
        self.content = content

    def set_box_key_visuals(self, element):
        """Handles keyVisualBox, which is actually a carousel of images.
        For the carousel to work in wordpress, we need the media IDs of the images,
        but we do not know these IDs before importing the media, so the content of the box
        is translated to parsable html and will be replaced by the adequate shortcode in the
        exporter.
        """
        elements = element.getElementsByTagName("image")
        content = "<ul>"
        for e in elements:
            if e.ELEMENT_NODE != e.nodeType:
                continue
            # URL is like /content/sites/<site_name>/files/file
            # splitted gives ['', content, sites, <site_name>, files, file]
            # result of join is files/file and we add the missing '/' in front.
            image_url = '/'.join(e.getAttribute("jahia:value").split("/")[4:])
            image_url = '/' + image_url
            content += '<li><img src="{}" /></li>'.format(image_url)
        content += "</ul>"
        self.content = content

    def _parse_links_to_list(self, element):
        """Handles link tags that can be found in linksBox and textBox

        Structure is the following:
        <linksList>
            <links>
                <linkDesc></linkDesc>  <-- It seems that sometimes this is not present in Jahia export
                <link>
                    <jahia:url>     <-- If not present, 'jahia:link' is present
                    <jahia:link>    <-- If not present, 'jahia:url' is present
                </link>
            </links>
        </linksList>
        """

        # Sorting parameters
        sort_params = element.getAttribute("jahia:sortHandler")

        # Default values that may be overrided later
        sort_way = 'asc'
        sort_tag_name = None

        # If we have parameters for sorting, they will look like :
        # epfl_simple_main_comboList_links_link;asc;false;false
        # https://pel.epfl.ch/awards_en
        if sort_params != "":
            # Extracting tag name where to find sort info
            # epfl_simple_main_comboList_links_link;asc;false;false ==> <jahia:link -> jahia:title attribute
            sort_tag_name = "jahia:{}".format(sort_params.split(';')[0].split('_')[-1])

            sort_way = sort_params.split(';')[1]

        links_boxes = BoxSortedGroup('', '', sort_way)

        elements = element.getElementsByTagName("links")
        for e in elements:
            if e.ELEMENT_NODE != e.nodeType:
                continue

            desc = ""
            title = ""
            url = ""

            # Sorting needed
            if sort_tag_name:
                sort_tags = e.getElementsByTagName(sort_tag_name)
                if sort_tags:
                    # It seems that, by default, it is the "jahia:title" value that is used for sorting
                    sort_value = sort_tags[0].getAttribute("jahia:title")

                # We don't have enough information to continue
                if not sort_tags or not sort_value:
                    raise Exception("No sort tag (%s) found (or empty sort value found)", sort_tag_name)
            else:
                # No sorting needed, we generate an ID for the box
                sort_value = len(links_boxes.boxes)

            # Going through 'linkDesc' and 'link' nodes
            for link_node in e.childNodes:
                if link_node.ELEMENT_NODE != link_node.nodeType:
                    continue

                if link_node.tagName == "linkDesc":
                    desc = link_node.getAttribute("jahia:value")
                elif link_node.tagName == "link":

                    # Going through node containing link. It can be 'jahia:link' or 'jahia:url' node.
                    for jahia_tag in link_node.childNodes:
                        if jahia_tag.ELEMENT_NODE != jahia_tag.nodeType:
                            continue

                        if jahia_tag.tagName in ['jahia:link', 'jahia:url']:
                            title = jahia_tag.getAttribute("jahia:title")

                        if jahia_tag.tagName == "jahia:link":

                            # It happens that a link references a page that does not exist anymore
                            # observed on site dii
                            try:
                                page = self.site.pages_by_uuid[jahia_tag.getAttribute("jahia:reference")]
                            except KeyError as e:
                                continue

                            # We generate "Jahia like" URL so exporter will be able to fix it with WordPress URL
                            url = "/page-{}-{}.html".format(page.pid, self.page_content.language)

                        elif jahia_tag.tagName == "jahia:url":
                            url = jahia_tag.getAttribute("jahia:value")

            link_html = '<li><a href="{}">{}</a>{}</li>'.format(url, title, desc)

            # Because boxes can be sortable, we use a BoxSortedGroup to handle this
            links_boxes.add_box_to_sort(link_html, sort_value)

        content = "<ul>{}</ul>".format(''.join(links_boxes.get_sorted_boxes()))

        if content == "<ul></ul>":
            content = ""

        return content

    def _parse_files_to_list(self, element):
        """Handles files tags that can be found in linksBox and textBox

        Structure is the following:
        <filesList>
            <files>
                <fileDisplayDetails></fileDisplayDetails>  <-- Boolean to tell if we have to display file details
                <fileDesc></fileDesc>  <-- may not be present (seems to be file details mentioned before)
                <file></file>  <-- path to file, no file title to display, we take filename.
            </files>
        </filesList>

        FIXME: property fileDisplayDetails is not handled for now because never find with 'true' value until now
        Maybe if value is set to 'true', we have to display content of 'fileDesc' property somewhere
        """
        elements = element.getElementsByTagName("file")
        content = "<ul>"
        for e in elements:
            if e.ELEMENT_NODE != e.nodeType:
                continue
            # URL is like /content/sites/<site_name>/files/file
            # splitted gives ['', content, sites, <site_name>, files, file]
            # result of join is files/file and we add the missing '/' in front.
            file_url = '/'.join(e.getAttribute("jahia:value").split("/")[4:])
            file_url = '/' + file_url
            file_name = file_url.split("/")[-1]
            content += '<li><a href="{}">{}</a></li>'.format(file_url, file_name)
        content += "</ul>"

        if content == "<ul></ul>":
            content = ""

        return content

    def set_box_map(self, element):
        """set the attributes of a map box"""

        self.shortcode_name = "epfl_map"

        # parse info
        query = Utils.get_tag_attribute(element, "query", "jahia:value")

        # in the parser we can't know the current language.
        # so we assign a string that we will replace by the current language in the exporter
        lang = self.UPDATE_LANG

        self.content = '[{} query="{}" lang="{}"]'.format(self.shortcode_name, query, lang)

    def fix_img_align_left(self):
        """
        Look for <img> having attribute "align" with value set to "left", delete it and add a "class='left'" instead
        This is done because, on Jahia, there's a mechanism (but we don't know where) which do this on the client side.
        :return:
        """
        soup = BeautifulSoup(self.content, 'html5lib')
        soup.body.hidden = True

        images = soup.find_all('img')

        for img in images:

            align = img.get('align')

            if align and align == 'left':
                img['class'] = 'left'
                del img['align']

        self.content = str(soup.body)

    def fix_video_iframes(self):
        """
        Look for :
            <iframe src="https://www.youtube.com...
            <iframe src="https://player.vimeo.com/video/...

        and replace with a shortcode
        :return:
        """
        soup = BeautifulSoup(self.content, 'html5lib')
        soup.body.hidden = True

        iframes = soup.find_all('iframe')

        for iframe in iframes:

            src = iframe.get('src')

            if src and ('youtube.com' in src or 'youtu.be' in src or 'player.vimeo.com' in src):

                shortcode = '[epfl_video url="{}"]'.format(src)
                # Replacing the iframe with shortcode text
                iframe.replaceWith(shortcode)

        self.content = str(soup.body)

    def add_id_to_h3(self):
        """
        Take title of <h3> elements, slugify it and add it as "id" attribute
        :return:
        """

        soup = BeautifulSoup(self.content, 'html5lib')
        soup.body.hidden = True

        h3s = soup.find_all('h3')

        for h3 in h3s:

            if h3.text != "" and h3.get('id') is None:
                slug = slugify(h3.text)
                h3['id'] = slug

        self.content = str(soup.body)

    def is_shortcode(self):
        return self.shortcode_name != ""

    def is_empty(self):
        return self.title == "" and self.content == ""

    def __str__(self):
        return self.type + " " + self.title
