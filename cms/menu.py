from menus.menu_pool import menu_pool
from menus.base import Menu, NavigationNode, Modifier
from cms.utils import get_language_from_request
from cms.utils.moderator import get_page_queryset, get_title_queryset
from django.conf import settings
from django.contrib.sites.models import Site
from cms.utils.i18n import get_fallback_languages
from cms.exceptions import NoHomeFound

def page_to_node(page, home, cut):
    parent_id = page.parent_id
    if home and page.parent_id == home.pk and cut:
        parent_id = None
    attr = {'navigation_extenders':page.navigation_extenders,
            'soft_root':page.soft_root,
            'auth_required':page.login_required,
            'reverse_id':page.reverse_id,}
    n = NavigationNode(page.get_menu_title(), 
                       page.get_absolute_url(), 
                       page.pk, 
                       parent_id, 
                       attr=attr,
                       )
    return n

class CMSMenu(Menu):
    
    def get_nodes(self, request):
        page_queryset = get_page_queryset(request)
        site = Site.objects.get_current()
        lang = get_language_from_request(request)
        try:
            home = page_queryset.get_home()
        except NoHomeFound:
            home = None
        filters = {
            'in_navigation':True,
            'site':site,
        }
        if settings.CMS_HIDE_UNTRANSLATED:
            filters['title_set__language'] = lang
        pages = page_queryset.published().filter(filters).order_by("tree_id", "lft")
        ids = []
        nodes = []
        first = True
        home_cut = False
        home_children = []
        for page in pages:
            if home:
                page.home_pk_cache = home.pk
                if first and page.pk != home.pk:
                    home_cut = True
                if (page.parent_id == home.pk or page.parent_id in home_children) and home_cut:
                    page.home_cut_cache = True 
                    home_children.append(page.pk)
            else:
                page.home_pk_cache = -1
            first = False
            ids.append(page.id)
        titles = list(get_title_queryset(request).filter(page__in=ids, language=lang))
        for page in pages:# add the title and slugs and some meta data
            for title in titles:
                if title.page_id == page.pk:
                    if not hasattr(page, "title_cache"):
                        page.title_cache = {}
                    page.title_cache[title.language] = title
                    nodes.append(page_to_node(page, home, home_cut))
                    ids.remove(page.pk)
        if ids: # get fallback languages
            fallbacks = get_fallback_languages(lang)
            for l in fallbacks:
                titles = list(get_title_queryset(request).filter(page__in=ids, language=l))
                for title in titles:
                    for page in pages:# add the title and slugs and some meta data
                        if title.page_id == page.pk:
                            if not hasattr(page, "title_cache"):
                                page.title_cache = {}
                            page.title_cache[title.language] = title
                            nodes.append(page_to_node(page, home, home_cut))
                            ids.remove(page.pk)
                            break
                if not ids:
                    break
        return nodes  
menu_pool.register_menu(CMSMenu)

class NavExtender(Modifier):
    def modify(self, request, nodes, namespace, id, post_cut, breadcrumb):
        if post_cut:
            return nodes
        exts = []
        # rearrange the parent relations
        for node in nodes:
            ext = node.attr.get("navigation_extenders", None)
            if ext:
                if not ext in exts:
                    exts.append(ext)
                for n in nodes:
                    if n.namespace == ext and not n.parent_id:
                        n.parent_id = node.id
                        n.parent_namespace = node.namespace
                        n.parent = node
                        node.children.append(n)
        removed = []
        # find all not assigned nodes
        for menu in menu_pool.menus.items():
            if hasattr(menu[1], 'cms_enabled') and menu[1].cms_enabled and not menu[0] in exts:
                for node in nodes:
                    if node.namespace == menu[0]:
                        removed.append(node)
        if removed or breadcrumb:
            # has home a nav extender and is home not in navigation?
            page_queryset = get_page_queryset(request)
            try:
                home = page_queryset.get_home()
            except NoHomeFound:
                home = None  
            if home and not home.in_navigation and home.navigation_extenders:
                n_removed = removed
                removed = []
                for node in n_removed:
                    if node.namespace != home.navigation_extenders:
                        removed.append(node)
            # if breadcrumb and home not in navigation add node
            if breadcrumb and home and not home.in_navigation:
                home = page_to_node(home, home, False)
                nodes.append(home)
                if request.path == home.get_absolute_url():
                    home.selected = True
                else:
                    home.selected = False
        # remove all nodes that are nav_extenders and not assigned 
        for node in removed:
            nodes.remove(node)
        return nodes   
menu_pool.register_modifier(NavExtender)


class SoftRootCutter(Modifier):
    def modify(self, request, nodes, namespace, id, post_cut, breadcrumb):
        if post_cut or not settings.CMS_SOFTROOT:
            return nodes
        selected = None
        root_nodes = []
        for node in nodes:
            if node.selected:
                selected = node
            if not node.parent:
                root_nodes.append(node)
        
        if selected:
            if selected.attr.get("soft_root", False):
                nodes = selected.get_descendants()
                selected.parent = None
                nodes = [selected] + nodes
            else:
                nodes = self.find_ancestors(selected, nodes)
            nodes = self.find_children(selected, nodes)
        else:
            for node in root_nodes:
                self.find_children(node, nodes)
        return nodes   
    
    def find_children(self, node, nodes):
        for n in node.children:
            if n.attr.get("soft_root", False):
                self.remove_children(n, nodes)
        return nodes
    
    def remove_children(self, node, nodes):
        for n in node.children:
            nodes.remove(n)
            self.remove_children(n, nodes)
        node.children = []
    
    def find_ancestors(self, node, nodes):
        is_root = False
        if node.parent:
            if node.parent.attr.get("soft_root", False):
                is_root = True
                nodes = node.parent.get_descendants()
                node.parent.parent = None
                nodes = [node.parent] + nodes
            else:
                nodes = self.find_ancestors(node.parent, nodes)
        else:
            for n in nodes:
                if n != node and not n.parent:
                    self.find_children(n, nodes)
        for n in node.children:
            if n != node:
                self.find_children(n, nodes)
            if is_root:
                n.parent = None
        return nodes
    
menu_pool.register_modifier(SoftRootCutter)