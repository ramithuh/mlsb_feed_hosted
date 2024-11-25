from collections import defaultdict

from atproto import models

import re
from server.logger import logger
from server.database import db, Post

ML_PATTERN = re.compile(r'(?i)(?:\b(?:machine|deep|geometric\s+deep)\s+learning\b|bioML|\b(?:neural\s+network(?:s)?|graph\s+neural\s+network(?:s)?|(?:protein\s+)?language\s+model(?:s)?|(?:ESM)-?\d*|(?:prot(?:BERT|einMPNN)|openFold|helixFold)|(?:GNINA|VINA)|flow-matching|boltz-\d*|diffusion\s+model(?:s)?|ColabFold|(?:pLM)s?|transformer(?:s)?|(?:LIGO|RFdiffusion|RoseTTAFold)|alphafold|AF[2-3]|GNN|VAE|ESMFold|OmegaFold|ProstQA)(?:\s*-?\s*(?:predicted|prediction|predictions))?\b|\bexplainable\b|\battention mechanism\b|\bfoundation model\b|\bfine-tuning\b|\bembedding\b|artificial intelligence|self-supervised|context-aware|context aware|zero-shot|pretraining|auxiliary tasks|latent space|equivariant|invariant|tensor-based|flow matching|optimal transport|featurisation|reinforcement learning|diffusion|active learning|masked modeling|inverse folding|representation learning|contrastive learning|linear probe|\bMCMC\b|generative model|\bIsomorphic Labs\b|\bRecursion Pharmaceuticals?\b|\bExscientia\b|\bAtomwise\b|\bInsilico Medicine\b|\bIktos\b)')

BIO_PATTERN = re.compile(r'(?i)(?:protein(s)?|enzyme(s)?|molecular biology|structural biology|\bpdb\b|peptide(s)?|amino acid(s)?|protein folding|molecular dynamic(s)?|molecular representation(s)?|ligand(s)? dock(ing|ed)|\bdock(ing|ed)?\b|\bmolecule representation\b|\bNMR\b|cryoem|cryo-em|conformation(al|s)?|\bbinding site(s)?\b|posebuster(s)?|\bkinase(s)?\b|\bmicrobio(logy|logical)?\b|\bBioML\b|genomic context(s)?|active site(s)?|enzyme design(s|ing)?|structural motif(s)?|protein sequence(s)?|structural proteome(s|ics)?|protein engineer(ing|ed)|protein.*?function(s|al)?|small molecule|protein.*?structure(s|al)?|\bPyMOL\b|\bChimeraX\b|\bVMD\b|\bstructural alignment(s)?\b|\bprotein-protein interaction(s)?\b|\bprotein complex(es)?\b|MMseqs|\bMSA\b|drug discovery|drug design|virtual screening|RNA structure|base pairs|pseudoknots|G-quadruplex|electrostatic potential|atomic model|biomolecule|macromolecule|\bPPI(s)?\b|crystallography|coevolution|phylogeny|\bside chain\b|backbone structure|backbone prediction|residue|biotherapeutics|protein design|binding affinity|binding pocket|protein surface|molecular surface|pharmacophore|TM[-\s]?score|[pl]?lddt|DrugDiscovery|DrugDesign|\bbinding\b)')


EXCLUDED_PATTERN = re.compile(r'(?i)\b(fuck(?:er|ing|ed|s)?|shit(?:ty|ting|ted|s)?|ass(?:hole|es|ed)?|bitch(?:es|ing|ed|y)?|cunt(?:s|ing|ed)?|dick(?:head|s|ed)?|bastard(?:s|ed)?|wank(?:er|ing|ed|s)?|twat(?:s|ted)?|whore(?:s|ing|ed)?|slut(?:ty|s)?|cock(?:s|ed)?|puss(?:y|ies)|turd(?:s)?|fag(?:got|s)?|prick(?:s|ed)?|retard(?:ed|s)?|bollock(?:s|ed)?|arse(?:s|hole|d)?|goddamn(?:ed|it)?|mother(?:fuck(?:er|ing))?|asshole(?:s)?|bullshit(?:ting|ted)?|porn(?:o|ography)?|lesb(?:ian|o|y|ians)?|gay(?:s)?|queer|homo(?:sexual)?|faggot(?:s)?|dyke(?:s)?|nigger(?:s)?|kike(?:s)?|spic(?:s)?|wetback(?:s)?|chink(?:s)?|paki(?:s)?|raghead(?:s)?|towelhead(?:s)?|tit(?:s|ties|ty)?|pony)\b')
EXCLUDED_PATTERN_2 = re.compile(r'(?i)(whey\s+(?:protein|powder)|protein\s+powder)')

import json

with open('/home/ruh/www/mlsb_feed_hosted/server/config_users.json', 'r') as config_file:
    config = json.load(config_file)

AUTO_INCLUDE_DIDS = set(config.get('auto_include_dids', []))
BIO_ONLY_DIDS = set(config.get('bio_only_dids', []))

def is_relevant_post(text: str, author_did: str) -> bool:
    """
    Determines if a post is relevant based on user category and content.

    Args:
        text (str): The text content of the post.
        author_did (str): The DID of the author.

    Returns:
        bool: True if the post is relevant, False otherwise.
    """
    # Auto-included users: Include all posts regardless of content
    if author_did in AUTO_INCLUDE_DIDS:
        return True

    if EXCLUDED_PATTERN_2.search(text):
        return False

    # Exclude posts containing inappropriate terms
    if EXCLUDED_PATTERN.search(text):
        return False

    # BIO-Only users: Must pass only the BIO check
    has_bio = bool(BIO_PATTERN.search(text))
    if author_did in BIO_ONLY_DIDS:
        return has_bio

    # General users: Must pass both ML and BIO checks
    has_ml = bool(ML_PATTERN.search(text))

    return has_ml and has_bio


def operations_callback(ops: defaultdict) -> None:
    # Here we can filter, process, run ML classification, etc.
    # After our feed alg we can save posts into our DB
    # Also, we should process deleted posts to remove them from our DB and keep it in sync

    # for example, let's create our custom feed that will contain all posts that contains alf related text

    posts_to_create = []
    for created_post in ops[models.ids.AppBskyFeedPost]['created']:
        author = created_post['author']
        record = created_post['record']

        # print all texts just as demo that data stream works
        post_with_images = isinstance(record.embed, models.AppBskyEmbedImages.Main)
        inlined_text = record.text.replace('\n', ' ')
        # logger.info(
        #     f'NEW POST '
        #     f'[CREATED_AT={record.created_at}]'
        #     f'[AUTHOR={author}]'
        #     f'[WITH_IMAGE={post_with_images}]'
        #     f': {inlined_text}'
        # )

        # # only alf-related posts
        # if 'alf' in record.text.lower():
        #     reply_root = reply_parent = None
        #     if record.reply:
        #         reply_root = record.reply.root.uri
        #         reply_parent = record.reply.parent.uri

        #     post_dict = {
        #         'uri': created_post['uri'],
        #         'cid': created_post['cid'],
        #         'reply_parent': reply_parent,
        #         'reply_root': reply_root,
        #     }
        #     posts_to_create.append(post_dict)

        # Apply our custom filter
        if is_relevant_post(record.text, author):
            reply_root = reply_parent = None
            if record.reply:
                reply_root = record.reply.root.uri
                reply_parent = record.reply.parent.uri

            post_dict = {
                'uri': created_post['uri'],
                'cid': created_post['cid'],
                'reply_parent': reply_parent,
                'reply_root': reply_root,
            }
            logger.info(
                f'NEW Relevant POST '
                f'[CREATED_AT={record.created_at}]'
                f'[AUTHOR={author}]'
            )
            posts_to_create.append(post_dict)

    posts_to_delete = ops[models.ids.AppBskyFeedPost]['deleted']
    if posts_to_delete:
        post_uris_to_delete = [post['uri'] for post in posts_to_delete]
        Post.delete().where(Post.uri.in_(post_uris_to_delete))
        # logger.info(f'Deleted from feed: {len(post_uris_to_delete)}')

    if posts_to_create:
        with db.atomic():
            for post_dict in posts_to_create:
                Post.create(**post_dict)
        logger.info(f'Added to feed: {len(posts_to_create)}')
