"""
Classes describing datasets of user-item interactions. Instances of these
are returned by dataset-fetching and dataset-processing functions.
"""

import numpy as np

import scipy.sparse as sp


class Interactions(object):
    """
    Interactions object. Contains (at a minimum) pair of user-item
    interactions. This is designed only for implicit feedback scenarios.

    Parameters
    ----------

    file_path: file contains (user,item,rating) triplets
    user_map: dict of user mapping
    item_map: dict of item mapping
    """

    def __init__(self, user_item_sequence, num_users, num_items):
        user_ids, item_ids = [], []
        for uid, item_seq in enumerate(user_item_sequence):
            for iid in item_seq:
                user_ids.append(uid)
                item_ids.append(iid)

        user_ids = np.asarray(user_ids)
        item_ids = np.asarray(item_ids)

        self.num_users = num_users
        self.num_items = num_items

        self.user_ids = user_ids
        self.item_ids = item_ids

        self.sequences = None
        self.test_sequences = None

    def __len__(self):

        return len(self.user_ids)

    def tocoo(self):
        """
        Transform to a scipy.sparse COO matrix.
        """

        row = self.user_ids
        col = self.item_ids
        data = np.ones(len(self))

        return sp.coo_matrix((data, (row, col)),
                             shape=(self.num_users, self.num_items))

    def tocsr(self):
        """
        Transform to a scipy.sparse CSR matrix.
        """

        return self.tocoo().tocsr()

    def to_sequence(self, sequence_length=5, target_length=1):
        """
        Transform to sequence form.

        Valid subsequences of users' interactions are returned. For
        example, if a user interacted with items [1, 2, 3, 4, 5, 6, 7, 8, 9], the
        returned interactions matrix at sequence length 5 and target length 3
        will be be given by:

        sequences:

           [[1, 2, 3, 4, 5],
            [2, 3, 4, 5, 6],
            [3, 4, 5, 6, 7]]

        targets:

           [[6, 7],
            [7, 8],
            [8, 9]]

        sequence for test (the last 'sequence_length' items of each user's sequence):

        [[5, 6, 7, 8, 9]]

        Parameters
        ----------

        sequence_length: int
            Sequence length. Subsequences shorter than this
            will be left-padded with zeros.
        target_length: int
            Sequence target length.
        """

        # # change the item index start from 1 as 0 is used for padding in sequences
        # for k, v in self.item_map.items():
        #     self.item_map[k] = v + 1
        # self.item_ids = self.item_ids + 1
        # self.num_items += 1

        max_sequence_length = sequence_length + target_length

        # Sort first by user id
        sort_indices = np.lexsort((self.user_ids,))

        user_ids = self.user_ids[sort_indices]
        item_ids = self.item_ids[sort_indices]

        user_ids, indices, counts = np.unique(user_ids,
                                              return_index=True,
                                              return_counts=True)
        # print(np.where(counts>50))
        # print(np.mean(counts))
        num_subsequences = sum([c - max_sequence_length + 1 if c >= max_sequence_length else 1 for c in counts])

        sequences = np.zeros((num_subsequences, sequence_length),
                             dtype=np.int64)
        sequences_targets = np.zeros((num_subsequences, target_length),
                                     dtype=np.int64)
        sequence_users = np.empty(num_subsequences,
                                  dtype=np.int64)

        test_sequences = np.zeros((self.num_users, sequence_length),
                                  dtype=np.int64)
        test_users = np.empty(self.num_users,
                              dtype=np.int64)

        _uid = None
        for i, (uid,
                item_seq) in enumerate(_generate_sequences(user_ids,
                                                           item_ids,
                                                           indices,
                                                           max_sequence_length)):
            if uid != _uid:
                test_sequences[uid][:] = item_seq[-sequence_length:]
                test_users[uid] = uid
                _uid = uid
            sequences_targets[i][:] = item_seq[-target_length:]
            sequences[i][:] = item_seq[:sequence_length]
            sequence_users[i] = uid

        self.sequences = SequenceInteractions(sequence_users, sequences, sequences_targets)
        self.test_sequences = SequenceInteractions(test_users, test_sequences)

    def to_newsequence(self, sequence_length=5, target_length=1):
        """
        Transform to sequence form.

        Valid subsequences of users' interactions are returned. For
        example, if a user interacted with items [1, 2, 3, 4, 5, 6, 7, 8, 9], the
        returned interactions matrix at sequence length 5 and target length 3
        will be be given by:

        sequences:

           [[1, 2, 3, 4, 5],
            [2, 3, 4, 5, 6],
            [3, 4, 5, 6, 7]]

        targets:

           [[6, 7],
            [7, 8],
            [8, 9]]

        sequence for test (the last 'sequence_length' items of each user's sequence):

        [[5, 6, 7, 8, 9]]

        Parameters
        ----------

        sequence_length: int
            Sequence length. Subsequences shorter than this
            will be left-padded with zeros.
        target_length: int
            Sequence target length.
        """
        max_sequence_length = sequence_length + target_length

        # Sort first by user id
        sort_indices = np.lexsort((self.user_ids,))

        user_ids = self.user_ids[sort_indices]
        item_ids = self.item_ids[sort_indices]

        user_ids, indices, counts = np.unique(user_ids,
                                              return_index=True,
                                              return_counts=True)

        num_subsequences = sum([ 1 for c in counts])


        _uid = None

        seq_user =[]
        sequences =[]
        sequences_targets =[]
        sequences_length =[]
        sequences_targetlen= []
        test_users = []
        test_sequences = []
        test_seq_length=[]
        for i,user_id in enumerate(user_ids):
            start_idx = indices[i]
            try:
                stop_idx = indices[i + 1]
            except:
                stop_idx = None
            one_sequence = item_ids[start_idx:stop_idx]
            if len(one_sequence)<=0:
                print(user_id,one_sequence,indices[i])
            if len(one_sequence)>sequence_length:
                one_sequence = one_sequence[-sequence_length:]

            test_train_seq = np.pad(one_sequence, (0, sequence_length-len(one_sequence)), 'constant')
            test_users.append(user_id)
            test_sequences.append(test_train_seq)
            test_seq_length.append(len(one_sequence))
            for train_len in range(len(one_sequence)-1):
                sub_seq = one_sequence[0:train_len+1]
                sequences_length.append(train_len+1)
                num_paddings = sequence_length-train_len-1
                sub_seq = np.pad(sub_seq, (0, num_paddings), 'constant')
                target_sub = one_sequence[train_len+1:train_len+1+target_length]
                target_len = len(target_sub)
                target_sub = np.pad(target_sub, (0, target_length-len(target_sub)), 'constant')
                seq_user.append(user_id)
                sequences.append(sub_seq)
                sequences_targetlen.append(target_len)
                sequences_targets.append(target_sub)
        sequence_users =np.array(seq_user)
        sequences =np.array(sequences)
        sequences_targetlen = np.array(sequences_targetlen)
        sequences_targets =np.array(sequences_targets)
        test_users = np.array(test_users)
        test_sequences = np.array(test_sequences)
        sequences_length = np.array(sequences_length)
        #print(sequences_length.shape)
        test_seq_length=np.array(test_seq_length)

        self.sequences = SequenceInteractions(sequence_users, sequences, targets=sequences_targets,length=sequences_length,tar_len=sequences_targetlen)
        self.test_sequences = SequenceInteractions(test_users, test_sequences,length=test_seq_length)


class SequenceInteractions(object):
    """
    Interactions encoded as a sequence matrix.

    Parameters
    ----------
    user_ids: np.array
        sequence users
    sequences: np.array
        The interactions sequence matrix, as produced by
        :func:`~Interactions.to_sequence`
    targets: np.array
        sequence targets
    """

    def __init__(self,
                 user_ids,
                 sequences,
                 targets=None,
                 length=None,
                 tar_len=None):
        self.user_ids = user_ids
        self.sequences = sequences
        self.targets = targets
        self.length = length
        self.tarlen = tar_len

        self.L = sequences.shape[1]
        self.T = None
        if np.any(targets):
            self.T = targets.shape[1]


def _sliding_window(tensor, window_size, step_size=1):
    if len(tensor) - window_size >= 0:
        # for i in range(len(tensor), 0, -step_size):
        #     if i - window_size >= 0:
        #         yield tensor[i - window_size:i]
        i = len(tensor)
        yield tensor[i - window_size:i]
            # else:
            #     break
    else:
        num_paddings = window_size - len(tensor)
        # Pad sequence with 0s if it is shorter than windows size.
        yield np.pad(tensor, (0, num_paddings), 'constant')


def _generate_sequences(user_ids, item_ids,
                        indices,
                        max_sequence_length):
    for i in range(len(indices)):

        start_idx = indices[i]

        if i >= len(indices) - 1:
            stop_idx = None
        else:
            stop_idx = indices[i + 1]

        for seq in _sliding_window(item_ids[start_idx:stop_idx],
                                   max_sequence_length):
            yield (user_ids[i], seq)
