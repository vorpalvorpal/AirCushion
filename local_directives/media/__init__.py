# $Id: customDirectivs.py$
# Author: Robin Shannon
# Copyright: MIT License

__docformat__ = 'reStructuredText'

import sys
import re
import langcodes
from urllib.parse import urlparse
from urllib.request import pathname2url
from docutils import nodes, utils
from docutils.nodes import fully_normalize_name, whitespace_normalize_name
from docutils.parsers.rst import Directive, directives, states
from docutils.parsers.rst.roles import set_classes
from mimetypes import guess_type
from distutils.util import strtobool
from tinycss2 import parse_declaration_list, ast 
from docutils.writers.docutils_xml import XMLTranslator

"""
create nodes
"""
class audio (nodes.image):
    pass

class source (nodes.General, nodes.Inline, nodes.Element):
    pass

class video (nodes.image):
    pass

class track (nodes.General, nodes.Inline, nodes.Element):
    pass

nodes._add_node_class_names(('audio', 'source', 'video', 'track'))

"""
Create base class 'Media'. 
This is the parent class to the Audio, Video and Image directives.
"""

class Media(Directive): # just define shared options and useful functions. Doesn't actually create nodes.
    messages = []
    contraindications = ('align', 'height', 'scale', 'width', 'no_fullscreen')

    def style_check(arg):
        if arg and arg.strip():
            # ensure valid css
            result = parse_declaration_list(arg)
            if any(isinstance(r, ast.ParseError) for r in result):
                print('fail')
                raise ValueError('\nStyle option does not contain valid css options. Ignoring style option')
                return None
            # ensure final semi-colon so we can add styles later
            if arg.strip().endswith(';'):
                arg = arg.strip() + ' '
            else:
                arg = arg.strip() + '; '
            return arg

    def add_style(self, key, value):
        pair = key + ': ' + self.option[value] + '; '
        del self.option[value]
        if 'style' in self.options:
            self.options['style'] += pair
        else:
            self.options['style'] = pair

    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'description': directives.unchanged, # include as text after source tags for audio/video and aria-labeledby
        'class': directives.class_option,
        'height': directives.length_or_percentage_or_unitless,
        'id': directives.class_option,
        'name': directives.unchanged, # creates name to be used from elsewhere in document to link here.
        'style': style_check,
        'width': directives.length_or_percentage_or_unitless,
    }

    def run(self, nodeMethod):
        if 'fullscreen' in self.options:
            try:
                self.options['class'].append(', media-fullscreen')
            except:
                self.options['class'] = ['media-fullscreen']
            del self.options['fullscreen']
        if 'height' in self.options:
            add_style('height', 'height')
        if 'width' in self.options:
            add_style('width', 'width')

        # create media node and return system messages
        set_classes(self.options)
        media_node = nodeMethod(self.block_text, **self.options)
        self.add_name(media_node)
        try:
            for node in self.source_nodes:
                media_node += node
        except:
            pass
        try:
            for node in self.track_nodes:
                media_node += node
        except:
            pass
        try:
            self.reference_node += media_node
            return self.reference_node
        except:
            return media_node
        
"""
Image Directive
This is based on the image directive from docutils, but adds the ability to define
an ID (useful for js/css manipulation), add styles directly in the image directive
(useful if you have a single css file used for multiple presentations you would 
prefer not to pollute), and the ability to define an image as fullscreen (which
requires .
"""

class Image(Media):
    align_v_values = ('top', 'middle', 'bottom')                                 
    align_va_values = align_v_values + ('baseline', 'sub', 'super', 'text-top', 'text-bottom')
    align_values = align_va_values + ('left', 'center', 'right')                                 
                                                                                 
    def align(arg):                                                         
        if arg and arg.strip():
            return directives.choice(arg, Media.align_values) 

    # If use of picture tag becomes widespread in future, use source tags like 
    # in audio/video rather than uri (src) option
    option_spec = Media.option_spec.copy()
    option_spec['align'] = align
    option_spec['alt'] = directives.unchanged # included as backwards-compatable version of 'description'
    option_spec['scale'] = directives.nonnegative_int
    option_spec['target'] = directives.unchanged
    option_spec['fullscreen'] = directives.flag

    def run(self):
        self.options['uri'] = directives.uri(self.arguments[0])
        if 'scale' in self.options:
            self.options['scale'] = 'scale(' + self.options['scale'] + ')'
            add_style('transform', 'scale')
        if 'alt' in self.options and not 'description' in self.options:
            self.options['description'] = self.options['alt']
            del self.options['alt']
        elif 'description' in self.options and 'alt' in self.options:
            self.state_machine.reporter.error(
                '\nError parsing the "%s" directive: \n'
                'The descirption and alt options are both specified. \n'
                'These options are synonymous. Only the value given for\n'
                'description ("%s") has been used'
                % (self.name, self.options['description']),
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
            del self.options['alt']
        # check align options
        if 'align' in self.options:                                              
            if isinstance(self.state, states.SubstitutionDef):                   
                # Check for align_v_values.                                      
                if self.options['align'] not in Media.align_v_values:             
                    self.state_machine.reporter.error(
                        'Error in "%s" directive: "%s" is not a valid value '    
                        'for the "align" option within a substitution '          
                        'definition.  Valid values for "align" are: "%s".'       
                        % (self.name, self.options['align'],                     
                           '", "'.join(Media.align_v_values)),                    
                        nodes.literal_block(self.block_text, self.block_text),
                        line=self.lineno)
            # align is not supported in the html5 spec, but is allowed by the
            # stadard docutils image directive. Convert align value to css 'float'
            # and 'vertical-align' properties.
            if self.options['align'] in align_va_values:
                add_style('vertical-align', 'align')
            elif self.options['align'] == 'center':
                add_style('float', 'None') # no css center option
            else:
                add_style('float', 'align')

        # raise error if fullscreen specified as well as contraindicated option
        if 'fullscreen' in self.options:
            for option in self.contraindications:
                if option in self.options:
                    self.state_machine.reporter.error(
                        'Error in %s directive: "%s" cannot be specified along \n'
                        'with the "fullscreen" option. The "%s" option has been \n'
                        'ignored.'
                        % (self.name, option, option),
                        nodes.literal_block(self.block_text, self.block_text),
                        line=self.lineno)
                    del self.options[option]

        self.generateReferenceNode()
        node = Media.run(self, nodes.image)
        return self.messages + [node]

    # add optional link around media node using nodes.reference
    def generateReferenceNode(self):
        self.reference_node = None
        if 'target' in self.options:
            block = states.escape2null(
                self.options['target']).splitlines()
            block = [line for line in block]
            target_type, data = self.state.parse_target(
                block, self.block_text, self.lineno)
            if target_type == 'refuri':
                self.reference_node = nodes.reference(refuri=data)
            elif target_type == 'refname':
                self.reference_node = nodes.reference(
                    refname=fully_normalize_name(data),
                    name=whitespace_normalize_name(data))
                self.reference_node.indirect_reference_name = data
                self.state.document.note_refname(self.reference_node)        
            else:                           # malformed target
                self.messages = data        # data is a system message
            del self.options['target']

class Audio(Media): 
    # TODO: xsl uses self.options['description'] as body content for video tag.
    # check that this is actually read by screen readers, and if not, think about
    # aria-label tag
    required_arguments = 1
    optional_arguments = sys.maxsize
    final_argument_whitespace = True
    option_spec = Media.option_spec.copy()
    option_spec['no_autoplay'] = directives.flag
    option_spec['no_controls'] = directives.flag
    option_spec['loop'] = directives.flag
    option_spec['muted'] = directives.flag
    option_spec['no_preload'] = directives.flag 
    option_spec['track'] = directives.unchanged
    node_name = audio
    has_content = True # for subtitle track list

    def run(self, *node_name):
        if node_name:
            self.node_name = node_name[0]
        if 'no_autoplay' in self.options:
            del self.options['no_autoplay']
        else:
            self.options['autoplay'] = None
        if 'no_controls' in self.options:
            del self.options['no_controls']
        else:
            self.options['controls'] = None
        if 'no_preload' in self.options:
            del self.options['no_preload']
        else:
            self.options['preload'] = None

        self.generateSourceNodes()
        self.generateTrackNodes()
        node = Media.run(self, self.node_name)
        return self.messages + [node]

    def generateSourceNodes(self):
        self.source_nodes = []
        for s in self.arguments:
            s = directives.uri(s)
            if not urlparse(s).scheme in ('http', 'https'):
                s = pathname2url(s) #converts windows path to unix path
            mime = guess_type(s)[0]
            if mime is not None:
                source_node = source(self.block_text, src=s, mime=mime)
                self.source_nodes.append([source_node])
                self.add_name(source_node)
            else:
                self.state_machine.reporter.error(
                    'Error in "%s" directive: "%s" is not of a valid filetype.\n' 
                    ' Preferred filetypes are: .webm and .ogg' 
                    % (self.name, s),
                    nodes.literal_block(self.block_text, self.block_text),
                    line=self.lineno)

    """
    Tracks are text files that provide metadata about a video. There are five kinds 
    of track recognised: subtitles, captions, descriptions, chapters, metadata. If
    no kind is given, subtitle is assumed. Tracks may be given either as a value to
    the :track: option or in the body of the directive. Only one track may be 
    specified in the :track: option, and it will have the 'default' label applied
    to it (this means it will be used automatically, unless the end user has
    specifically requested something else). If defined in the body of the directive
    individual tracks should be given as list items in a bullet list. Either way, 
    tracks are described by the following syntax: 
    
    filename (language/kind) "label" 

    Because language is only allowed if kind is "subtitle", providing a language
    implicitly selects "subtitle" as kind. Languages must be BCP 47 language codes.
    Labels are user readable descriptions of the track.
    """

    def generateTrackNodes(self):
        self.track_nodes = []
        if 'track' in self.options:
            track_node = self.parse_track(self.options['track'])
            track_node.default = True
            self.track_nodes.append(track_node)

        # parse directive body
        # create anonymous container for parsing
        node = nodes.Element()         
        # take indented block, parse it and put the output into node
        self.state.nested_parse(self.content, self.content_offset, node)
        # If appropriate input has been given node should now be a list-like 
        # object of the following form:
        # [Element[bullet_list[list_item[paragraph[Text]]]]]
        if self.check_for_list(node):
            for list_item in node[0]:
                list_item = list_item[0][0].strip().replace('\n', ' ').replace('\r', '')
                self.track_nodes.append(self.parse_track(list_item))

        if len(self.track_nodes) > 0:
            self.add_name(self.track_nodes)
        else:
            del self.track_nodes

    def check_for_list(self, node):
        if len(node) is 0:
            return False # no track specified 
        elif len(node) > 1 or not isinstance(node[0], nodes.bullet_list):
            self.state_machine.reporter.error(
                'Error parsing content block for the "%s" directive: \n'
                'The only content allowed in %s directive is a single \n'
                'bullet list representing %s tracks. List items should \n'
                'take the form "* filename.vtt (lang/kind) \'label\'". '
                % (self.name, self.name, self.name),
                nodes.literal_block(self.block_text, self.block_text),
                line=self.lineno)
        # Check bullet list is flat (does not contain child lists):
        for i in range(len(node[0])):
            list_item = node[0][i]
            if len(list_item) is not 1 or not isinstance(list_item[0], nodes.paragraph):
                self.state_machine.reporter.error(
                    'Error parsing content block for the "%s" directive: \n'
                    'single-level bullet list of %s tracks expected.'
                    % (self.name, self.name), nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
        return True # single level bullet list found

    def parse_track(self, item):
        options = {}
        original = item
        try:
            head, _emptyStr, kind, _emptyStr, tail = re.split(r"(^| )\((.*?)\)( |$)", item)
            item = head + ' ' + tail
            kind = kind.strip()
            if kind not in ('captions', 'descriptions', 'chapters', 'metadata'):
                if langcodes.code_to_names('language', langcodes.get(kind).language):
                    # kind is a recognised language code
                    language = langcodes.standardize_tag(kind)
                else:
                    # kind is not a lang code. Try interpreting as a language name
                    try:
                        language = str(langcodes.find(kind))
                    except:
                        self.state_machine.reporter.error(
                            'Error in "%s" directive: track language "%s" is unknown. \n' 
                            'Track languages should be given as BCP 47 compliant \n'
                            'language codes.'
                            % (self.name, kind), nodes.literal_block(
                            self.block_text, self.block_text), line=self.lineno)
                        language = kind
                options['kind'] = 'subtitles'
                options['language'] = language
            else:
                options['kind'] = kind
        except:
            self.state_machine.reporter.error(
                'Error in "%s" directive: \n'
                'the track "%s" does not follow the form:\n'
                'filename.vtt (kind/language) "label"'
                % (self.name, original), nodes.literal_block(
                self.block_text, self.block_text), line=self.lineno)
            # defualt to english subtitles
            options['kind'] = 'subtitles'
            options['language'] = 'en'
        try:
            head, _emptyStr, _quote, label, _emptyStr, tail = re.split(r"""(^| )(["'])(.*?)\2( |$)""", item)
            if head and tail:
                self.state_machine.reporter.error(
                    'Error in "%s" directive: \n'
                    'the track "%s" does not follow the form:\n'
                    'filename.vtt (kind/language) "label"'
                    % (self.name, original), nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
            item = head + tail
            options['label'] = label.strip()
        except:
            try:
                options['label'] = langcodes.get(language).autonym()
            except:
                self.state_machine.reporter.error(
                    'Error in "%s" directive: track must have a label'
                    % (self.name), nodes.literal_block(
                    self.block_text, self.block_text), line=self.lineno)
        options['src'] = directives.uri(item)
        track_node = track(self.block_text, **options)
        return track_node

class Video(Audio): 
    option_spec = Audio.option_spec.copy()
    option_spec['poster'] = directives.uri
    option_spec['no_fullscreen'] = directives.flag
    node_name = video

    def run(self):
        self.options['fullscreen'] = None
        for option in Media.contraindications:
            if option in self.options:
                del self.options['fullscreen']
                break
        node = Audio.run(self, self.node_name)
        return self.messages + node
        
# Register directives

directives.register_directive('image', Image)
directives.register_directive('video', Video)
directives.register_directive('audio', Audio)
