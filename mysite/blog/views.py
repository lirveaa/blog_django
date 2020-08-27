from django.shortcuts import render, get_object_or_404,HttpResponseRedirect
from .models import Post, Comment
from django.core.paginator import Paginator, EmptyPage,\
    PageNotAnInteger
from django.views.generic import ListView,CreateView, UpdateView
from django.core.mail import send_mail
from taggit.models import Tag
from django.db.models import Count,Q
from django.contrib.postgres.search import TrigramSimilarity
from django.contrib.postgres.search import SearchVector,SearchQuery,SearchRank
from .forms import EmailPostForm, CommentForm, SearchForm, PostForm,EditForm,Category
from  operator import attrgetter
def CategoryView(request, cats):
    category_posts = Post.objects.filter(category=cats)
    return render(request, 'blog/post/categories.html', {'cats':cats, 'category_posts':category_posts})

def post_share(request, post_id):
    # Retrieve post by id
    post = get_object_or_404(Post, id=post_id, status='published')
    sent = False

    if request.method == 'POST':
    # Form was submitted
        form = EmailPostForm(request.POST)
        if form.is_valid():
            # Form fields passed validation
            cd = form.cleaned_data
            post_url = request.build_absolute_uri(
                post.get_absolute_url())
            subject = f"{cd['name']} recommends you read " \
                      f"{post.title}"
            message = f"Read {post.title} at {post_url}\n\n" \
                      f"{cd['name']}\'s comments: {cd['comments']}"
            send_mail(subject, message, 'lirvess@gmail.com',
                      [cd['to']])
            sent = True
    else:
        form = EmailPostForm()
    return render(request, 'blog/post/share.html', {'post': post,
                                                    'form': form,
                                                    'sent': sent})
class PostListView(ListView):
    queryset = Post.published.all()
    context_object_name = 'posts'
    paginate_by = 3
    template_name = 'blog/post/list.html'

def post_list(request, tag_slug=None):
    search_query = request.GET.get("search", "")
    if search_query:
        posts = Post.objects.filter(Q(title__icontains=search_query) | Q(body__icontains=search_query))
    else:
        posts = Post.objects.all()
    object_list = posts
    #paginator = Paginator(object_list, 3)  # 3 posts in each page
    tag = None

    if tag_slug:
        tag = get_object_or_404(Tag, slug=tag_slug)

    paginator = Paginator(object_list, 1)  # 3 posts in each page
    page = request.GET.get('page')
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer deliver the first page
        posts = paginator.page(1)
    except EmptyPage:
        # If page is out of range deliver last page of results
        posts = paginator.page(paginator.num_pages)

    return render(request,
                  'blog/post/list.html',
                  {'page': page,
                   'posts': posts,
                   'tag': tag })


def post_detail(request, year, month, day, post):
    context = {}


    post = get_object_or_404(Post, slug=post,
                             status='published',
                             publish__year=year,
                             publish__month=month,
                             publish__day=day)
    # List of active comments for this post
    comments = post.comments.filter(active=True)

    new_comment = None

    if request.method == 'POST':
        # A comment was posted
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            # Create Comment object but don't save to database yet
            new_comment = comment_form.save(commit=False)
            # Assign the current post to the comment
            new_comment.post = post
            # Save the comment to the database
            new_comment.save()
            comment_form = CommentForm()

    else:
        comment_form = CommentForm()

        # List of similar posts
    post_tags_ids = post.tags.values_list('id', flat=True)
    similar_posts = Post.published.filter(tags__in=post_tags_ids) \
            .exclude(id=post.id)
    similar_posts = similar_posts.annotate(same_tags=Count('tags')) \
            .order_by('-same_tags', '-publish')[:4]

    return render(request,
                 'blog/post/detail.html',
                 {'post': post,
                   'comments':comments,
                   'new_comment': new_comment,
                   'comment_form': comment_form,
                  'similar_posts': similar_posts})

def post_search(request):
    context = {}
    query = ""
    if request.GET:
        query = request.GET['q']
        context['query'] = str(query)
    blog_posts = sorted(get_blog_queryset(query), key=attrgetter('updated'), reverse=True)
    context['blog_posts'] = blog_posts

    return render(request, 'blog/post/search.html', context)
    #
    # form = SearchForm()
    # query = None
    # results = []
    # if 'query' in request.GET:
    #     form = SearchForm(request.GET)
    #     if form.is_valid():
    #         query = form.cleaned_data['query']
    #         results = Post.published.annotate(
    #             similarity=TrigramSimilarity('title', query),
    #         ).filter(similarity__gt=0.1).order_by('-similarity')
    # return render(request,
    #             'blog/post/search.html',
    #             {'form': form,
    #             'query': query,
    #             'results': results})

class AddPostView(CreateView):
    model =  Post
    form_class = PostForm
    template_name = 'blog/post/add_post.html'



class AddCategoryView(UpdateView):
    model = Category
    template_name = 'blog/post/add_category.html'
    fields = '__all__'

class UpdatePostView(UpdateView):
    model = Post
    template_name = 'blog/post/update_post.html'
    fields = '__all__'

def get_blog_queryset(query=None):
    queryset = []
    queries = query.split(" ")
    for q in queries:
        posts = Post.objects.filter(
            Q(title__icontains=q),
            Q(title__icontains=q)
        ).distinct()

        for post in posts:
            queryset.append(post)

    return list(set(queryset))
